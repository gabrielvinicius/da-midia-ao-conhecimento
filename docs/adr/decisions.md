# Architecture Decision Records (ADR) - Video Summarizer

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
*   **Status:** Aceito
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
