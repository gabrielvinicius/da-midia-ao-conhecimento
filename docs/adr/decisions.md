# Architecture Decision Records (ADR) - Da Mídia ao Conhecimento

Decisões de arquitetura do sistema e o motivo de cada uma. As regras do dia a dia estão em `AGENTS.md`.

## [ADR-001] Pure Dependency Injection (Composition Root)
*   **Status:** Aceito
*   **Contexto:** O uso de singletons globais e injeção implícita tornava o sistema difícil de testar e acoplava o domínio à infraestrutura.
*   **Decisão:** Centralizar a construção de todos os módulos no `main.py` usando fábricas `bootstrap.py`.
*   **Consequência:** Testabilidade total, previsibilidade de instâncias e facilidade de substituição de adaptadores (ex: Storage).

## [ADR-002] Granular Pipeline para Análise de Texto
*   **Status:** Aceito
*   **Contexto:** A análise de texto era um monólito procedimental. Falhas no final do processo descartavam resultados úteis do início.
*   **Decisão:** Implementar o padrão *Pipeline* com passos independentes e persistência parcial.
*   **Consequência:** Resiliência a falhas de IA e possibilidade de salvar sentimentos/tópicos mesmo se a sumarização falhar.

## [ADR-003] Orquestração Inteligente (Hardware Advisor)
*   **Status:** Aceito
*   **Contexto:** Workers de IA frequentemente sofrem de OOM (Out Of Memory) ou travamentos sob carga pesada.
*   **Decisão:** Criar um `HardwareAdvisor` que lê CPU, memória e VRAM e informa o nível de carga ao painel e à interface; os modelos rodam um por vez no worker pesado e são liberados ao fim de cada etapa.
*   **Consequência:** O usuário vê quando o sistema está sobrecarregado. Tarefas travadas são encerradas pelo prazo de processamento e pelo limite de tempo das tarefas (ADR-009).

## [ADR-004] Evolução do esquema por migrações; análise como documento JSONB
*   **Status:** Aceito (substitui a proposta de *upcasting* em leitura, que não foi implementada)
*   **Contexto:** O esquema muda com o sistema, e a análise tem campos que crescem a cada etapa nova.
*   **Decisão:** Todo o esquema é criado e alterado só por migrações do Alembic, aplicadas quando o backend inicia; a CI cria um banco vazio pelas migrações, compara com os modelos e as desfaz e refaz. A análise é um documento JSONB lido e gravado por inteiro.
*   **Consequência:** Campos novos da análise não exigem migração; consultas que cruzam análises ficam mais difíceis (não fazem parte dos requisitos).

## [ADR-005] Sincronização Realtime via WebSocket Flattening
*   **Status:** Aceito
*   **Contexto:** O frontend recebia notificações aninhadas que exigiam lógica complexa de roteamento na UI.
*   **Decisão:** "Aplanar" (flatten) o payload do WebSocket no backend para que campos como `kind` e `media_id` fiquem no topo.
*   **Consequência:** Código do frontend simplificado e atualização reativa instantânea.

## [ADR-006] Inteligência Multimodal (Visão + Áudio)
*   **Status:** Aceito; o modelo de visão padrão mudou no ADR-011
*   **Contexto:** A análise era baseada apenas em áudio, ignorando o contexto visual valioso de vídeos.
*   **Decisão:** Integrar o modelo Moondream 2 no pipeline para descrever frames chave e enriquecer o resumo.
*   **Consequência:** Insights mais profundos e precisos, transformando o sistema de transcritor em analista de vídeo.

## [ADR-007] Pesquisa Semântica Global via pgvector
*   **Status:** Aceito
*   **Contexto:** Não era possível buscar conhecimento através de múltiplos arquivos processados.
*   **Decisão:** Implementar a extensão `pgvector` no Postgres e criar um índice vetorial de todos os trechos processados.
*   **Consequência:** O sistema torna-se uma Base de Conhecimento global capaz de responder perguntas por significado.

## [ADR-008] Human-in-the-loop (Feedback Cycle)
*   **Status:** Aceito
*   **Contexto:** O sistema era autônomo, mas não aprendia com as correções dos usuários.
*   **Decisão:** Implementar um mecanismo de feedback (pontuação) e correção manual de resumos com trilha de auditoria.
*   **Consequência:** Criação de um dataset de alta qualidade para melhoria contínua dos modelos de IA.

## [ADR-009] Workers no mesmo repositório e na mesma imagem da API
*   **Status:** Aceito
*   **Contexto:** Foi avaliado mover os workers do Celery para um repositório ou submódulo próprio.
*   **Decisão:** Manter API e workers na mesma base de código e na mesma imagem, como dois tipos de processo (monólito modular). As tarefas são finas e usam os mesmos domínios, casos de uso e adaptadores. `src/celery_app.py` guarda só a configuração (usada pela API para enviar tarefas); `src/worker_process.py` monta cada processo de worker, com as reações dos módulos em ordem.
*   **Consequência:** Uma mudança de evento ou de esquema é uma alteração só, sem pacote compartilhado versionado nem duas CIs. Separar passaria a valer se outra equipe mantivesse o worker de GPU ou se o worker usasse outro runtime; uma imagem leve só para a API pode ser feita com dois alvos no Dockerfile, sem mover código.

## [ADR-010] Eventos em memória por processo, sem barramento distribuído
*   **Status:** Aceito
*   **Contexto:** Os módulos reagem aos eventos uns dos outros, e API e workers rodam em processos diferentes.
*   **Decisão:** Dentro de cada processo, eventos tipados num barramento em memória; entre processos, tarefas na fila do Celery (pelo nome) e o banco; avisos ao usuário pelo Redis. Não há Kafka nem tabela de saída de eventos (*outbox*).
*   **Consequência:** Um anúncio pode se perder se o processo cair entre gravar e publicar; varreduras periódicas (mídias paradas, sem processamento ou em análise além do prazo) e o reanúncio na reentrega da tarefa cobrem esse caso, o que basta numa instalação de uma só máquina.

## [ADR-011] Quadros descritos pelo mesmo modelo do resumo (Qwen3.5 via Ollama)
*   **Status:** Aceito
*   **Contexto:** O Moondream 2 descrevia os quadros em inglês e de forma genérica ("um homem fala ao microfone"), ocupava ~4 GB a mais da GPU e falhava em silêncio quando as dependências mudavam (faltavam `torchvision` e `einops`; o código do modelo não funciona com o `transformers` 4.50+).
*   **Decisão:** `VISUAL_PROVIDER=ollama` por padrão: o Qwen3.5-9B, que já faz o resumo e aceita imagens, descreve os quadros em português, transcrevendo os textos da tela e sem supor o que não está visível. Descrições seguidas da mesma cena ficam uma vez só. O Moondream continua como opção.
*   **Consequência:** Nos mesmos quadros de uma aula, o Qwen3.5 leu os nomes dos autores do Manifesto Ágil e o título de um livro que o Moondream não leu; custa ~4 s por quadro (Moondream, ~2 s).

## [ADR-012] Reranqueador na busca, na CPU da API
*   **Status:** Aceito
*   **Contexto:** Só com os vetores do e5-small, o trecho certo ficava em 1º lugar em 4 de 8 perguntas formuladas com outras palavras (aula de 30 min).
*   **Decisão:** A busca traz os 20 trechos mais parecidos pelos vetores e o `BAAI/bge-reranker-v2-m3` os reordena lendo pergunta e trecho juntos (`RerankerPort`). Roda na CPU da API, ao lado do vetor da pergunta; se falhar, vale a ordem dos vetores.
*   **Consequência:** 7 de 8 em 1º lugar; ~2,5 s por busca e ~2 GB de memória na API. A API não roda os modelos da análise (eles ficam nos workers), mas roda esses dois modelos leves da busca.

## [ADR-013] Gênero, capítulos e perguntas: o modelo escreve, os dados decidem
*   **Status:** Aceito
*   **Contexto:** Um resumo de vídeo opinativo afirmava as teses do apresentador como fatos; pedir ao modelo os horários dos capítulos deu capítulos até "17:30" numa aula de 30 min.
*   **Decisão:** O gênero do conteúdo é identificado antes do resumo, com trechos do início, meio e fim, e orienta o prompt. Os cortes dos capítulos vêm das sequências de trechos do mesmo tema (sem temas, a cada ~5 min); o modelo só dá os títulos. As perguntas de revisão apontam o número do capítulo, que o sistema converte no horário.
*   **Consequência:** Horários sempre coerentes com a gravação; uma chamada curta a mais por análise para cada recurso (~1 s, ~3 s e ~7 s medidos).

## [ADR-014] PyTorch 2.14 com CUDA 12.6
*   **Status:** Aceito (substitui o 2.5.1 com CUDA 12.4)
*   **Contexto:** O PyTorch 2.5 já não carrega pesos `.bin` com bibliotecas novas (CVE-2025-32434) e impede dependências que exigem 2.8+ (como o `pyannote.audio` 4, para identificar quem fala).
*   **Decisão:** `torch==2.14.1` e `torchvision==0.29.1`, do índice cu126 (rocm7.2 para AMD, cpu sem GPU). CUDA 12, e não 13, porque a transcrição (CTranslate2 4.8) carrega as bibliotecas do CUDA 12.
*   **Consequência:** Comparado ao 2.5.1 na RTX 3060, mesmos resultados, tempos e memória em todos os modelos e 429 testes passando. A variante AMD passa a exigir um driver compatível com o ROCm 7.2.

## [ADR-015] Preservação da revisão humana e recuperação da conclusão da análise
*   **Status:** Aceito
*   **Contexto:** A nova análise reutiliza o ID, mas seus checkpoints substituem o resultado anterior, inclusive correções humanas. O fluxo automático também carrega texto na fila e lê segmentos atuais, podendo misturar versões. Falhas de checkpoint são ignoradas, o carregamento inicial de embeddings pode ficar indisponível no cache e uma falha ao atualizar a mídia pode deixar uma análise concluída com estado incorreto.
*   **Decisão:** Implementar as seguintes garantias sem alterar a topologia do monólito:
    - Uma análise com resumo, temas, capítulos ou perguntas revisados não pode ser regenerada pela operação de nova análise: a API responde 409. O worker verifica a mesma regra; a persistência dos checkpoints gerados usa bloqueio da linha e revalida a revisão para proteger também correções feitas durante a execução. Exclusão e reprocessamento completo de mídia com falha conservam sua política explícita de limpeza.
    - O texto, os segmentos, o idioma e o contexto visual de uma mídia são lidos da mesma fonte no worker. A fila automática passa identificadores; mensagens antigas com texto embutido continuam aceitas, mas esse texto não prevalece sobre a fonte persistida. Pedidos que apontem para uma transcrição já substituída são ignorados sem afetar o processamento atual; fontes ausentes ou sem texto não são substituídas por texto antigo da fila.
    - Falha ao gravar checkpoint interrompe a execução e chega à política de retry. Checkpoints preservam resultados parciais; não representam retomada por etapa. Cada retry continua executando o pipeline inteiro.
    - A análise persiste um campo tipado `pipeline_completed` somente depois de terminar o pipeline. A recuperação periódica consulta os resultados concluídos por uma porta implementada pelo módulo de análise antes de marcar uma mídia parada como falha; um resultado concluído reconcilia a mídia para `completed`. A inferência não é repetida apenas para corrigir esse estado. Falhas na consulta não autorizam marcar a mídia como falha.
    - O adapter de embeddings confirma a inicialização somente após carregar o modelo. Uma falha temporária permite uma nova tentativa; um bloqueio protege a inicialização concorrente na API.
*   **Consequências:** Revisões humanas ganham proteção tanto no pedido quanto na gravação. Mensagens do fluxo automático ficam menores e coerentes. As análises concluídas podem recuperar o estado mesmo quando o anúncio se perde. O JSONB aceita o novo marcador sem migração de tabela; resultados anteriores sem o marcador não são considerados conclusões comprovadas pela recuperação.
*   **Limites:** Esta decisão não introduz outbox, histórico versionado de execuções, deduplicação entre workers ou retomada por etapa. Reanalisar conteúdo revisado exige uma futura operação explícita com histórico, em vez de substituir correções silenciosamente. Validação com adapters simulados não comprova inferência real ou consumo de GPU.

## [ADR-016] Cadeia de suprimentos da CI: ações por commit, token mínimo e imagens varridas
*   **Status:** Aceito
*   **Contexto:** As ações dos workflows eram referenciadas por tag (`actions/checkout@v4`), que o dono do repositório pode mover para outro código; em março de 2026, as tags do `trivy-action` foram reescritas para código malicioso (CVE-2026-33634), e só quem fixava o commit escapou. O `ci.yml` não declarava `permissions`, e o token recebia o padrão do repositório. Nenhuma imagem era construída na CI: um Dockerfile quebrado ou uma biblioteca de sistema vulnerável só apareciam na implantação, já na máquina de produção. A execução manual do `Deploy` aceitava qualquer ramo, e a regra de ramo do ambiente `producao` não vale em repositório privado no plano gratuito. Também não havia atualização automática de dependências, a CI usava o Redis 7 contra o 8.8 da produção, e o modelo de PR e o `Makefile` descreviam ferramentas que o projeto não usa (Poetry, mypy, `.venv/bin`).
*   **Decisão:** Seguir as recomendações de segurança do GitHub Actions e as verificações do OpenSSF Scorecard (Pinned-Dependencies, Token-Permissions, Dependency-Update-Tool):
    - Toda ação é fixada pelo commit, com a versão em comentário, e o checkout não guarda a credencial (`persist-credentials: false`). O Dependabot atualiza ações, pacotes Python e npm, imagens base e imagens do Compose em PRs semanais agrupados; torch, torchvision e o `transformers` ≥ 4.50 ficam de fora, pelas restrições do ADR-014 e do Moondream.
    - Os workflows declaram `permissions: contents: read`; quem precisa de mais (Gemini) pede por job.
    - O job `deployment` passa a verificar os Dockerfiles (hadolint), os workflows (actionlint) e falhas de segurança neles (zizmor). Exceções ficam justificadas no próprio arquivo (`.hadolint.yaml`, comentários `zizmor: ignore`).
    - O workflow `images.yml` constrói a interface e o backend (variante CPU: a CUDA não cabe no runner), sobe a imagem num teste rápido e a varre com o Trivy; uma vulnerabilidade crítica com correção disponível reprova. Roda nos PRs que tocam imagens ou dependências, em todo push na main e toda semana.
    - O `Deploy` manual só roda a partir da main; a saída entre passos usa `GITHUB_OUTPUT`, e não `GITHUB_ENV`.
*   **Consequências:** Uma tag comprometida deixa de alterar o que a CI executa, e as atualizações chegam como PRs revisáveis. Um erro de imagem aparece no PR, não na implantação. O custo é um PR do Dependabot por ecossistema por semana e cerca de 15 minutos de CI quando a imagem do backend é reconstruída.
*   **Limites:** Sem proteção da main (indisponível no plano), um merge com a CI vermelha continua possível; a implantação, porém, só acontece com a CI verde. A imagem de GPU não é varrida antes de entrar em produção, só a de CPU, que tem as mesmas camadas de sistema. Não há assinatura das imagens nem SBOM publicado: as imagens não saem da máquina de produção (ADR-017).

## [ADR-017] Execução: Compose de nó único endurecido, imagens versionadas pelo commit e migrações separadas
*   **Status:** Aceito
*   **Contexto:** A produção é uma máquina com GPU NVIDIA rodando Docker Desktop, e a revisão da infraestrutura encontrou:
    - **Logs:** o driver padrão (`json-file`) não rotaciona, e os logs dos contêineres cresciam sem limite.
    - **Imagens:** `app:latest` era remarcada como `previous` a cada implantação, sem saber de que commit vinha. Sem limpeza, a máquina acumulava 46 GB de imagens e 21 GB de cache de build.
    - **Migrações:** o entrypoint da API as aplicava, e os workers dependiam da API só por isso.
    - **Saúde dos workers:** eles não tinham verificação de saúde; um worker sem conexão aparecia como "Up".
    - **Nomes fixos:** `container_name` e redes com nome fixo impediam uma segunda instância (de teste) na mesma máquina.
    - **MinIO:** a imagem `minio:latest` deixou de ser publicada em outubro de 2025, e uma instalação nova falhava ao baixá-la. Além disso, o bucket padrão fazia a opção S3 aparecer sem servidor S3.
    - **Túnel:** o `deploy.ps1` decidia por expressão regular se subia o túnel da Cloudflare.
*   **Decisão:** Manter o Docker Compose num nó só (Kubernetes ou Swarm não se pagam com uma GPU e um operador, e a documentação do Docker trata o Compose num servidor como forma válida de produção) e aplicar o que o Docker e o CIS Docker Benchmark recomendam:
    - **Logs:** driver `local` (5 arquivos de 20 MB por contêiner).
    - **Privilégios:** `no-new-privileges` em todos os serviços; `cap_drop: [ALL]` nos nossos, que rodam sem root. Cada imagem foi testada com essas restrições.
    - **Imagens versionadas pelo commit:** a implantação constrói `app:<commit>` e `frontend:<commit>`, marca `current` quando a versão fica saudável e, se não ficar, sobe a anterior sem reconstruir. Ficam três versões e uma semana de cache de build. A revisão do commit vai no rótulo OCI da imagem.
    - **Migrações:** no serviço `migrate`, executado uma vez antes da API e dos workers (`service_completed_successfully`).
    - **Saúde dos workers:** verificação pelo `celery inspect ping`, respondido pelo processo principal mesmo com uma transcrição em andamento.
    - **Nomes derivados do projeto** para contêineres e redes.
    - **Perfis opcionais** em `COMPOSE_PROFILES`: `internet` (túnel) e `s3` (MinIO da Chainguard, fixado pelo digest). Sem bucket, só o armazenamento local é oferecido.
    - **Testes** garantem rotação de logs, `no-new-privileges`, versões fixas e ausência de `container_name`.
*   **Consequências:** Uma instalação nova volta a subir. O disco deixa de encher com logs e imagens antigas, e a versão em execução é identificável pelo commit. Voltar atrás leva segundos e funciona sem internet. Os contêineres e as redes passam a ter nomes como `video-summarizer-backend-1`, então `docker compose exec backend` continua valendo, mas não `docker exec backend`.
*   **Limites:**
    - As imagens não vão para um registro: a do backend tem 13 GB, e a cota de pacotes de um repositório privado gratuito é de 500 MB. Por isso não há assinatura (cosign) nem SBOM publicado, e a imagem de GPU é construída na própria máquina.
    - Uma migração que remove colunas impede a volta à versão anterior; migrações devem ser compatíveis com a versão anterior (expandir e depois contrair).
    - Docker Desktop no Windows não é um servidor: depende da sessão do usuário (ADR-018). O caminho natural de evolução é um host Linux com Docker Engine e o mesmo Compose.

## [ADR-018] Operação: cópias com restic, teste de restauração e runner vigiado
*   **Status:** Aceito
*   **Contexto:** As cópias de segurança eram manuais e completas: cada uma copiava todas as mídias (2,2 GB em outubro de 2026, crescendo a cada envio), sem retenção, sem verificação e sem teste de restauração. Ao serem rodados na pasta de produção, os scripts não achavam o projeto e gravavam um banco vazio sem acusar erro. O runner do GitHub parou em 10/10/2026, quando sua janela foi fechada, e ficou três dias parado com implantações na fila. A tarefa agendada só tinha o gatilho de logon e "reiniciar se falhar", que o Agendador do Windows não aplica quando o processo termina depois de iniciado.
*   **Decisão:**
    - **Cópias:** repositório restic (incremental, com deduplicação e criptografia) com o banco (`pg_dump -Fc`) e as mídias. Retenção de 14 diárias, 8 semanais e 12 mensais, e `restic check` ao final de cada execução.
    - **Agendamento:** o workflow `Backup` roda todo dia no runner de produção. O histórico fica na aba Actions, e uma falha avisa por e-mail.
    - **Teste de restauração:** aos domingos, o banco mais recente é restaurado num PostgreSQL temporário e conferido por consultas (tabelas, migração, usuários, mídias), e 5% dos dados do repositório são lidos de volta.
    - **Runner:** continua na sessão do usuário, porque o Docker Desktop também precisa dela e, como serviço do Windows, o runner subiria sem Docker. A tarefa é recriada por `install-runner-task.ps1`, com o runner num laço e um gatilho a cada 5 minutos que o inicia se não estiver rodando.
*   **Consequências:** A segunda cópia do mesmo dia levou 12 s e gravou 2,6 MB, contra 2,2 GB por cópia antes. A primeira restauração testada recuperou 10 tabelas, 3 usuários e 22 mídias. Uma cópia que não restaura passa a ser descoberta na semana, e não no dia em que for preciso usá-la.
*   **Limites:** A regra 3-2-1 ainda não é cumprida, porque não há cópia fora da máquina. O mesmo script aceita um repositório remoto do restic (`s3:`, `b2:`, `rclone:`), e uma segunda cópia remota é o próximo passo. A chave do repositório precisa ser guardada fora da máquina. Também não há alertas: o Prometheus coleta métricas, mas nada avisa quando um worker cai ou a fila cresce (o próximo passo seria Alertmanager com regras para workers fora do ar, fila parada e disco cheio).
