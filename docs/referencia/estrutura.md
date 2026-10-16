# Estrutura do repositório

O repositório reúne tudo o que se implanta junto: a API e os workers, a
interface web e a implantação. O relatório do TCC fica num repositório à parte
(`relatorio_tcc`).

## Raiz

| Caminho | Conteúdo |
|---|---|
| `main.py` | Ponto de entrada da API (FastAPI): monta os módulos e as rotas |
| `src/` | Código do backend, um pacote por módulo |
| `frontend/` | Interface web (React 19, TypeScript, Vite, Tailwind) |
| `alembic/` | Migrações do banco, aplicadas pelo serviço `migrate` |
| `tests/` | Testes do backend (veja abaixo) |
| `docker/` | Arquivos montados nos contêineres (`garage.toml`, `prometheus.yml`, entrada do worker) e a imagem do site da documentação (`docs.Dockerfile`) |
| `scripts/ops/` | Implantação, cópias de segurança e tarefa do runner ([Comandos](comandos.md)) |
| `scripts/evaluation/` | Medições do protocolo de avaliação do TCC (WER, tempos) |
| `scripts/docs/` | Gerador da referência desta documentação e conversor para a Wiki |
| `docs/` | Esta documentação e os ADRs |
| `zensical.toml` | Site da documentação: menu, tema e extensões do Markdown |
| `docker-compose.yml` | Produção; `docker-compose.cpu.yml`, `.rocm.yml` e `.dev.yml` só sobrescrevem o que muda |
| `Dockerfile` | Imagem da API e dos workers (a mesma, com comandos diferentes) |
| `.env.example` | Todas as configurações, comentadas ([referência](configuracao.md)) |
| `.importlinter` | Fronteiras entre módulos e camadas, conferidas pelo `lint-imports` |
| `AGENTS.md` | Regras do código, para pessoas e assistentes de IA |
| `.github/` | Workflows (CI, imagens, implantação, cópias, Wiki), Dependabot e modelo de PR |

## Módulos do backend (`src/`)

Cada módulo é um contexto delimitado, com o próprio domínio e as próprias
tabelas ([Arquitetura](../explicacao/arquitetura.md)).

| Módulo | Responsável por |
|---|---|
| `media_management` | Envio (inclusive em partes), estados da mídia, exclusão, reprocessamento e reprodução |
| `media_processing` | Transcrição (Whisper), descrição dos quadros, extração de texto com OCR e o pedido de análise |
| `text_analysis` | Pipeline da análise (trechos, vetores, temas, gênero, resumo, capítulos, perguntas, fidelidade), busca, revisão e estudo |
| `notifications` | Avisos ao usuário, gravados e entregues em tempo real pelo WebSocket |
| `user_management` | Contas, login, sessão, tokens, e-mails da conta |
| `storage` | Portas e adaptadores de armazenamento (local e S3) e limpeza de arquivos |
| `admin` | Painel do administrador: estatísticas, fila, servidor, qualidade, usuários |
| `shared` | Núcleo compartilhado: eventos, erros, relógio, regra de acesso, e a infraestrutura comum (banco, barramento, logs, métricas) |

Além deles: `src/celery_app.py` (configuração do Celery, importada também pela
API) e `src/worker_process.py` (montagem de cada processo de worker).

### Dentro de um módulo

| Pasta | Conteúdo |
|---|---|
| `domain/` | Entidades e regras, sem dependência de framework |
| `application/` | Casos de uso e serviços; `ports.py` declara o que eles precisam do mundo |
| `infrastructure/` | Adaptadores (banco, modelos, filas), persistência e `dependencies/builders.py` (a fábrica de cada serviço) |
| `api/` | Rotas e esquemas da API |
| `config/` | Configuração do módulo (variáveis de ambiente) |
| `tasks.py`, `worker.py`, `bootstrap.py` | Na raiz do módulo: tarefas do Celery, reações aos eventos nos workers e montagem na API |

## Testes (`tests/`)

| Pasta | O que testa |
|---|---|
| `unit/` | Regras e serviços com as dependências simuladas, e os testes de arquitetura (dono das tabelas, dono dos eventos, composição única, implantação) |
| `integration/` | Portas e adaptadores; os de PostgreSQL rodam com `TEST_POSTGRES_URL` |
| `smoke/` | A API sobe e responde |
| `e2e/` | Fluxo completo pela API, com PostgreSQL e Redis |
| `mocks/`, `utils/` | Dublês e utilitários dos testes |

Os testes da interface ficam em `frontend/` (Vitest ao lado dos componentes e
Playwright em `frontend/tests/e2e`).
