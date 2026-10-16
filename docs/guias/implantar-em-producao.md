# Implantar em produção

Este guia prepara uma máquina para rodar o sistema em produção, com
implantação contínua: a cada merge na `main` com a CI verde, a máquina se
atualiza sozinha e volta à versão anterior se a nova não ficar saudável.

A configuração de referência é a máquina de avaliação do TCC: Windows 11 com
Docker Desktop (WSL 2) e uma GPU NVIDIA de 12 GB. Para os motivos dessas
escolhas, veja [Operação e confiabilidade](../explicacao/operacao.md) e os
ADRs 017 e 018.

## Pré-requisitos

- **Windows 11** com WSL 2 e o driver NVIDIA atualizado (a GPU chega aos
  contêineres pelo WSL; confira com `nvidia-smi` no PowerShell).
- **Docker Desktop** com o Compose 2.24 ou mais recente.
- **Git for Windows**, instalado em `C:\Program Files\Git` (o workflow de
  cópias de segurança usa o Git Bash desse caminho).
- **PowerShell 7** (`pwsh`), usado pelo workflow de implantação.
- Acesso de administrador ao repositório no GitHub (para registrar o runner e
  criar as variáveis).

## 1. Crie a pasta de produção

A produção é um clone separado do repositório, com o próprio `.env`. O
workflow muda essa pasta para o commit aprovado; não trabalhe nela.

```powershell
git clone https://github.com/gabrielvinicius/da-midia-ao-conhecimento.git C:\producao\da-midia-ao-conhecimento
cd C:\producao\da-midia-ao-conhecimento
Copy-Item .env.example .env
```

## 2. Configure o `.env`

Além dos valores do [tutorial](../tutoriais/primeiros-passos.md#1-baixe-o-código-e-crie-a-configuração)
(`DB_PASSWORD`, `SECRET_KEY` e o primeiro administrador), defina:

| Variável | Para quê |
|---|---|
| `PUBLIC_URL` | Endereço pelo qual as pessoas acessam (vai nos links dos e-mails) |
| `SMTP_*` | Envio de e-mails: confirmação do cadastro e "Esqueci minha senha" (opcional) |
| `COMPOSE_PROFILES` | Serviços opcionais: `internet` (túnel) e `s3` (Garage) |
| `MEDIA_STORAGE_PATH` | Pasta do host para as mídias, de preferência outro disco (opcional) |
| `BACKUP_REPOSITORY`, `BACKUP_PASSWORD` | Repositório e chave das cópias de segurança |

Os detalhes de cada um estão nos guias [Publicar na internet](publicar-na-internet.md),
[Armazenamento](armazenamento.md) e [Cópias de segurança](copias-de-seguranca.md);
a lista completa, na [referência da configuração](../referencia/configuracao.md).

> [!IMPORTANT]
> Guarde `BACKUP_PASSWORD` e `SECRET_KEY` num gerenciador de senhas, fora da
> máquina. Sem a chave das cópias, nenhuma delas pode ser restaurada.

## 3. Suba o sistema pela primeira vez

```powershell
docker compose up -d --build
docker compose ps
```

Espere todos os serviços ficarem `healthy`. Na primeira vez, o serviço
`ollama-models` baixa o modelo de linguagem principal e o reserva.

## 4. Registre o runner do GitHub

A implantação roda num runner instalado na própria máquina. Assim nenhuma
porta fica aberta para a internet e nenhuma credencial do servidor vai para o
GitHub.

1. No GitHub: **Settings > Actions > Runners > New self-hosted runner**,
   sistema **Windows x64**. Siga os comandos de download na pasta
   `C:\actions-runner`.
2. Na configuração, acrescente o rótulo `producao`:

   ```powershell
   cd C:\actions-runner
   .\config.cmd --url https://github.com/gabrielvinicius/da-midia-ao-conhecimento --token <token da página> --labels producao
   ```

   Responda **não** à pergunta sobre rodar como serviço: o Docker Desktop só
   funciona na sessão do usuário, e o runner precisa estar nela também.
3. Instale a tarefa que mantém o runner no ar, abre o Docker Desktop e confere
   a cada 5 minutos se ele está rodando:

   ```powershell
   cd C:\producao\da-midia-ao-conhecimento
   pwsh scripts/ops/install-runner-task.ps1
   ```

## 5. Crie as variáveis do repositório

Em **Settings > Secrets and variables > Actions > Variables**:

| Variável | Valor |
|---|---|
| `DEPLOY_DIR` | `C:\producao\da-midia-ao-conhecimento` |
| `PUBLIC_URL` | O endereço público (aparece na página do ambiente `producao`) |

## 6. Confira a implantação contínua

Dispare uma implantação manual: **Actions > Deploy > Run workflow** (só na
`main`). O workflow:

1. muda a pasta de produção para o commit que passou na CI;
2. roda `scripts/ops/deploy.ps1`, que constrói as imagens marcadas com o
   commit (`app:<commit>`, `frontend:<commit>`), sobe os serviços e espera o
   backend ficar saudável e a interface responder em `/api/health`;
3. marca a versão saudável também como `current` e guarda só as três últimas;
4. se a verificação de saúde falhar, sobe de novo a versão anterior, sem
   reconstruir nada, e o workflow termina com erro.

Confira a versão no ar pela coluna da imagem:

```powershell
docker compose ps --format "{{.Service}} {{.Image}} {{.Status}}"
```

## Voltar a uma versão anterior à mão

As imagens das três últimas versões ficam na máquina. Para voltar a uma delas
sem reconstruir:

```powershell
docker images app            # mostra as versões guardadas
$env:APP_TAG = "<commit>"
docker compose up -d --no-build
```

A implantação seguinte, ou um `Run workflow` do Deploy, devolve a produção à
`main`.

## Veja também

- [Cópias de segurança](copias-de-seguranca.md): o workflow diário usa o
  mesmo runner.
- [Solucionar problemas](solucionar-problemas.md#implantação-parada-na-fila):
  runner parado e implantação na fila.
- [Comandos](../referencia/comandos.md): os scripts de operação.
