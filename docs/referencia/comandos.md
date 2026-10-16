# Comandos

Os comandos do dia a dia, na pasta do projeto (na produção,
`C:\producao\da-midia-ao-conhecimento`). Os scripts `.sh` rodam no Git Bash
no Windows; os `.ps1`, no PowerShell 7.

## Operação

| Tarefa | Comando |
|---|---|
| Ver o que está no ar (e a versão) | `docker compose ps --format "{{.Service}} {{.Image}} {{.Status}}"` |
| Logs de um serviço | `docker compose logs -f backend` |
| Reiniciar um serviço | `docker compose restart <serviço>` |
| Aplicar mudanças do `.env` | `docker compose up -d` |
| Reimplantar a `main` | GitHub: Actions > Deploy > Run workflow |
| Implantar a versão da pasta à mão | `pwsh scripts/ops/deploy.ps1` |
| Voltar a uma versão guardada | `$env:APP_TAG = "<commit>"; docker compose up -d --no-build` |
| Versões guardadas | `docker images app` |
| Reinstalar a tarefa do runner | `pwsh scripts/ops/install-runner-task.ps1` |

Os logs usam o driver `local` do Docker, com rotação de 5 arquivos de 20 MB por
contêiner.

## Cópias de segurança

| Tarefa | Comando |
|---|---|
| Copiar agora | `sh scripts/ops/backup.sh`, ou Actions > Backup > Run workflow |
| Testar a restauração | `sh scripts/ops/verify-backup.sh`, ou o Backup com **verify** |
| Restaurar a mais recente | `sh scripts/ops/restore.sh` |
| Restaurar uma específica | `sh scripts/ops/restore.sh <snapshot>` |
| Listar as cópias | `. scripts/ops/restic-env.sh && restic "$RESTIC_IMAGE" snapshots` |

Variáveis lidas do `.env`: `BACKUP_REPOSITORY`, `BACKUP_PASSWORD` e
`BACKUP_KEEP_DAILY`, `_WEEKLY`, `_MONTHLY`. `ENV_FILE` aponta outro arquivo de
variáveis (usado nos testes). Veja [Cópias de segurança](../guias/copias-de-seguranca.md).

## `deploy.ps1`

| Parâmetro | Padrão | Uso |
|---|---|---|
| `-PreviousSha` | (vazio) | Commit para o qual voltar se a nova versão não ficar saudável (o workflow passa o que estava no ar) |
| `-HealthUrl` | `http://localhost:3000/api/health` | Endereço conferido depois de subir |
| `-HealthTimeoutSeconds` | `600` | Tempo máximo até a versão nova ficar saudável |
| `-KeepVersions` | `3` | Quantas versões guardar (as mais antigas e o cache de build com mais de uma semana saem) |

## Monitoramento

| O que | Onde |
|---|---|
| Saúde da API, do banco e do Redis | `http://localhost:3000/api/health` (503 se algum falhar) |
| Métricas (Prometheus) | `http://localhost:9090` na própria máquina; de fora, pelo túnel com o Cloudflare Access |
| Rastros das requisições e tarefas (Jaeger) | `http://localhost:16686` na própria máquina; de fora, pelo túnel com o Cloudflare Access |
| Fila, servidor e qualidade das análises | Interface: Administração |

## Desenvolvimento

| Tarefa | Comando |
|---|---|
| Subir com o código do host | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` |
| Criar uma migração | `alembic revision --autogenerate -m "<descrição>"` |
| Aplicar as migrações | `alembic upgrade head` (no Compose, o serviço `migrate` faz isso) |
| Testes do backend | `pytest tests/unit tests/smoke tests/integration -q` |
| Verificações do backend | `ruff check src tests main.py` e `lint-imports` |
| Testes da interface | `npm run test:ci` e `npm run test:e2e`, em `frontend/` |
| Regerar a referência da documentação | `python scripts/docs/gerar_referencia.py` |
| Ver o site da documentação | `pip install -r requirements-docs.txt` e `zensical serve` (em `http://localhost:8000`) |

Os comandos completos da CI estão em [Desenvolver](../guias/desenvolver.md).
