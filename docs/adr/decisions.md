# Architecture Decision Records (ADR) - Video Summarizer

Este documento registra as decisões arquiteturais críticas que levaram o sistema ao **Nível 6.0**.

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
*   **Decisão:** Criar um `HardwareAdvisor` que monitora VRAM/CPU em tempo real e adapta a estratégia de processamento proativamente.
*   **Consequência:** Redução drástica de falhas fatais e melhor aproveitamento da GPU.

## [ADR-004] Zero-Downtime Schema Evolution (JSONB Upcasting)
*   **Status:** Aceito
*   **Contexto:** Migrações relacionais em campos complexos exigiam downtime ou bloqueios de tabela.
*   **Decisão:** Utilizar versionamento de payload JSONB e lógica de `upcasting` (conversão em tempo de leitura) no repositório.
*   **Consequência:** Deploy contínuo sem janelas de manutenção para mudanças no modelo de dados da análise.

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
