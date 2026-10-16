# Desenvolver

Como montar o ambiente, rodar as mesmas verificações da CI e abrir um PR que
passa na revisão. As regras completas do código estão em
[`AGENTS.md`](https://github.com/gabrielvinicius/da-midia-ao-conhecimento/blob/main/AGENTS.md); aqui ficam os passos.

## Ambiente

**Backend** (Python 3.12):

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -r requirements-dev.txt
```

O PyTorch vem do índice da variante (CPU para desenvolver; a imagem de
produção usa CUDA 12.6). Não existe Poetry.

**Frontend** (Node 24):

```bash
cd frontend
npm ci
VITE_API_URL=http://localhost:8000 npm run dev   # http://localhost:5173
```

Sem `VITE_API_URL`, a interface procura a API em `/api` no próprio endereço,
como faz atrás do Nginx na instalação com o Compose. A API já aceita
`localhost:5173` no CORS (`CORS_ORIGINS`). No PowerShell, defina a variável
antes: `$env:VITE_API_URL = "http://localhost:8000"`.

**Tudo em contêineres**, com o código do host montado e a API recarregando
sozinha:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Verificações (as mesmas da CI)

**Backend**, na raiz:

```bash
ruff check src tests main.py --select E9,F63,F7,F82,F401,F811,F841
ruff check src --select C901 --config 'lint.mccabe.max-complexity=12'
lint-imports                                   # fronteiras entre módulos e camadas
pytest tests/unit tests/smoke tests/integration -q
```

- Os testes que precisam de PostgreSQL rodam com `TEST_POSTGRES_URL`
  apontando para um banco de teste; sem ela, são pulados.
- Os de ponta a ponta (`tests/e2e`) precisam de PostgreSQL e Redis; o passo
  correspondente de `.github/workflows/ci.yml` mostra as variáveis.

**Frontend**, em `frontend/`:

```bash
npm run typecheck
npm run lint                 # inclui as regras do React Compiler
npm run test:ci              # Vitest
npm run build
npm run test:e2e             # Playwright, com a API simulada
```

**Infraestrutura**: o job `deployment` da CI confere os arquivos do Compose,
os scripts (ShellCheck), os Dockerfiles (hadolint) e os workflows (actionlint
e zizmor). O job `docs` confere esta documentação (veja abaixo).

## Regras que mais aparecem na revisão

O resumo; os detalhes e os motivos estão em `AGENTS.md` e nos ADRs.

- **Camadas**: domínio, aplicação e infraestrutura. O domínio e a aplicação
  falam com o mundo só por portas (`application/ports.py`); os adaptadores
  ficam em `infrastructure/`. O `lint-imports` impede atalhos.
- **Composição num lugar só**: cada serviço tem uma fábrica, em
  `infrastructure/dependencies/builders.py`, usada pela API, pelos workers e
  pelas reações a eventos.
- **Cada módulo, suas tabelas**: para saber de dados de outro módulo, defina
  uma porta e deixe esse módulo implementá-la.
- **Eventos tipados**: cada evento tem um único módulo que o publica, e os
  campos são tipados, nunca um dicionário livre.
- **Sem substitutos silenciosos**: um modelo que não carregou gera erro, e não
  uma saída inventada.
- **Frontend**: valores derivados na renderização, e não copiados num efeito;
  funções passadas ao `setState` são puras (o React 19 pode rodá-las depois).
- **Complexidade**: funções com complexidade de McCabe até 12.

## Mudou rotas, configurações ou eventos?

A referência da documentação é gerada a partir do código. Regere-a e inclua o
resultado no PR:

```bash
python scripts/docs/gerar_referencia.py
```

O teste `tests/unit/test_docs_reference.py` falha se ela ficar desatualizada.
Ao mudar comportamento, atualize também o guia ou a explicação
correspondente em `docs/`, no mesmo PR.

Uma página nova entra também no menu do site, em `nav` no `zensical.toml`.
Para ver o site como ele será publicado:

```bash
pip install -r requirements-docs.txt
zensical serve
```

A CI gera o site em modo estrito (`zensical build --strict`): um link para
uma página que não existe reprova o PR.

## Commits e PRs

- **Commits** no padrão Conventional Commits: `feat(storage): ...`,
  `fix(media): ...`, `docs: ...`.
- **PR** com o que mudou, por quê e como foi validado (saída dos testes,
  medições, capturas). Uma decisão de arquitetura nova vira um ADR em
  `docs/adr/decisions.md`.
- O merge na `main` com a CI verde **implanta na produção** sozinho (veja
  [Implantar em produção](implantar-em-producao.md)).

## Veja também

- [Estrutura do repositório](../referencia/estrutura.md): onde fica cada coisa.
- [Arquitetura](../explicacao/arquitetura.md): por que as regras acima existem.
- [Atualizar dependências](atualizar-dependencias.md): PRs do Dependabot.
