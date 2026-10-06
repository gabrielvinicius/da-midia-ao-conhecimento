# Video Summarizer (backend)

Plataforma que transcreve aulas gravadas e documentos, resume o conteúdo,
identifica temas e tom, e permite buscar trechos pelo significado. Roda
inteira numa única máquina, sem enviar dados para fora.

## Arquitetura

Monólito modular em DDD hexagonal: cada módulo (`media_management`,
`media_processing`, `text_analysis`, `notifications`, `user_management`,
`storage`, `admin`) tem domínio, aplicação, infraestrutura e API, e as
fronteiras são verificadas pelo `lint-imports` (`.importlinter`).

- **API** (FastAPI): recebe envios, consultas e revisões; nunca roda modelos.
- **Workers** (Celery + Redis): o pesado (GPU, uma tarefa por vez) transcreve,
  extrai texto e analisa; o leve roda as verificações periódicas.
  A configuração fica em `src/celery_app.py`; a montagem de cada processo de
  worker, em `src/worker_process.py`.
- **Eventos**: dentro de cada processo, um barramento em memória liga os
  módulos; entre processos, as tarefas seguem pela fila e os avisos ao
  usuário pelo Redis. Varreduras periódicas recuperam o que se perder.

As regras do projeto estão em `AGENTS.md`.

## Tecnologias

- Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17 com pgvector
- Celery 5 e Redis 8
- faster-whisper (transcrição), Moondream 2 (quadros de vídeo), Ollama com
  Qwen3.5 9B e Gemma 4 de reserva (resumo), sentence-transformers e BERTopic
- Docker Compose, com variantes para GPU NVIDIA (CUDA 12.4), AMD (ROCm) e CPU

## Implantação

```bash
git clone --recurse-submodules <repositório>
cp .env.example .env        # defina SECRET_KEY, DB_PASSWORD e o administrador
docker compose up -d --build
```

- **Variantes**: sem GPU, `-f docker-compose.yml -f docker-compose.cpu.yml`;
  GPU AMD, `-f docker-compose.yml -f docker-compose.rocm.yml`.
- **Desenvolvimento** com o código do host (a API recarrega sozinha):
  `-f docker-compose.yml -f docker-compose.dev.yml`.
- **Cópia de segurança**: `sh scripts/ops/backup.sh` grava o banco e as mídias
  em `backups/<data>`; `sh scripts/ops/restore.sh backups/<data>` restaura.
- **Acesso pela rede**: a interface responde por HTTP na porta 3000. Para
  HTTPS, coloque um proxy reverso com certificado na frente e defina
  `USER_COOKIE_SECURE=true` no `.env`.

**Instalações anteriores a esta versão**: o banco ficava num volume anônimo,
que um `docker compose down` descartava. Para levá-lo ao volume correto:

```bash
git pull
sh scripts/ops/backup.sh                 # com a versão antiga ainda no ar
docker compose up -d --build             # sobe com o volume novo (banco vazio)
sh scripts/ops/restore.sh backups/<data> # devolve banco e mídias
```

## Dependências

- `requirements.txt`: execução (API e workers), com as versões testadas.
- `requirements-dev.txt`: testes e verificações; não vão para a imagem.

## Verificações (as mesmas da CI)

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check src tests main.py --select E9,F63,F7,F82,F401,F811,F841
ruff check src --select C901 --config 'lint.mccabe.max-complexity=12'
lint-imports
pytest tests/unit tests/smoke tests/integration -q
```

Os testes de ponta a ponta (`tests/e2e`) precisam de PostgreSQL e Redis; veja
o passo correspondente em `.github/workflows/ci.yml`.
