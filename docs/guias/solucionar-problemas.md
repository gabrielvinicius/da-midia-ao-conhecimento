# Solucionar problemas

Sintoma, causa provável e correção dos problemas já vistos neste sistema. Cada
caso aconteceu de verdade; a data ajuda a achar o PR ou o ADR correspondente.

Antes de tudo, o estado geral:

```powershell
docker compose ps --format "{{.Service}} {{.Image}} {{.Status}}"
docker compose logs --since 30m backend worker-heavy | Select-String '"level": "error"'
```

## Endereço público responde 530

**Sintoma:** a página pública mostra o erro 530 da Cloudflare.

**Causa:** o túnel (`cloudflared`) não está conectado. Em 15/10/2026, a máquina
desligou numa queda de energia e voltou sem o Docker Desktop, que não abria
sozinho no logon: o runner subiu, e o sistema ficou fora.

**Correção:**

1. Confira se o Docker responde: `docker info`. Se não, abra o Docker Desktop.
   Os contêineres voltam sozinhos (`restart: unless-stopped`).
2. Confira se o perfil `internet` está em `COMPOSE_PROFILES` e se o serviço
   `cloudflared` está no ar.
3. Para evitar a repetição, reinstale a tarefa do runner, que abre o Docker
   Desktop antes do runner: `pwsh scripts/ops/install-runner-task.ps1`.

## Login recusado

**Sintoma:** "E-mail ou senha incorretos" para uma conta que existe.

**Diagnóstico:** o log registra o e-mail mascarado, com um código no final
(`g***@gmail.com#ffd7`). O código é um resumo do e-mail inteiro: compare-o com
o das contas cadastradas para saber se o e-mail digitado é exatamente o
cadastrado.

```powershell
docker compose logs --since 1h backend | Select-String 'auth.authenticate'
```

**Correção:**

- Se o e-mail confere, é a senha: use **Esqueci minha senha** na tela de login
  (com o envio de e-mails configurado).
- Sem e-mail configurado, redefina a senha do administrador pelo `.env`:
  `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD` e
  `DEFAULT_ADMIN_FORCE_PASSWORD=1`, reinicie o `backend` e, depois de entrar,
  apague a senha e volte o `FORCE_PASSWORD` para `0`.
- Depois de cinco falhas seguidas, o login daquele e-mail fica bloqueado por
  15 minutos (`USER_LOGIN_*`).

## Implantação parada na fila

**Sintoma:** o workflow Deploy fica em *Queued* e nada muda na produção.

**Causa:** o runner `producao` está desligado. Em 10/10/2026, a janela do
runner foi fechada e ele ficou três dias parado.

**Correção:**

```powershell
Get-ScheduledTask -TaskName 'GitHub Actions Runner (producao)'
Get-Content C:\actions-runner\runner.log -Tail 30
pwsh scripts/ops/install-runner-task.ps1   # se a tarefa não existir ou estiver diferente
```

A tarefa confere a cada 5 minutos se o runner está rodando.

## Implantação voltou à versão anterior

**Sintoma:** o Deploy termina com erro e a produção continua na versão
anterior.

**Causa:** a versão nova não ficou saudável em até 10 minutos, e o
`deploy.ps1` subiu de novo a anterior. É o comportamento esperado.

**Correção:** o log do workflow mostra qual serviço não ficou saudável. Veja o
log dele e corrija na `main`; a implantação seguinte tenta de novo.

```powershell
docker compose logs --tail 100 backend
```

## Cópia de segurança falhou

**Sintoma:** e-mail do GitHub com o workflow Backup em vermelho.

**Causas já vistas:**

- **Shell errado** (15/10/2026): no PATH do runner, `bash` é o do WSL, que não
  acha o script gerado pelo runner. O workflow usa o Git Bash pelo caminho
  curto `C:\PROGRA~1\Git\bin\bash.exe`; confira se o Git for Windows está
  instalado nesse caminho.
- **Banco fora do ar**: o `pg_dump` falha e a cópia é interrompida antes de
  gravar um dump vazio.
- **Repositório inacessível**: a pasta de `BACKUP_REPOSITORY` sumiu (disco
  desconectado) ou a chave mudou.

**Correção:** leia o passo que falhou no log do workflow e rode o mesmo
script na pasta de produção (`sh scripts/ops/backup.sh`), pelo Git Bash.

## Mídia parada em "Processando" ou "Analisando"

**Sintoma:** uma mídia não sai do estado por muito tempo.

**Causa:** o worker foi interrompido (reinício, falta de memória) no meio da
tarefa. As verificações periódicas do `worker-light` dão a mídia como falha
depois do prazo (`MEDIA_ANALYSIS_GIVE_UP_MINUTES` para a análise), com o
motivo.

**Correção:** em **Administração > Fila**, as mídias paradas aparecem
marcadas. Quando forem dadas como falha, o dono vê **Tentar novamente**, e o
administrador pode reprocessar todas as falhas de uma vez em
**Administração > Mídias**.

## Interface responde 502 depois de recriar o backend

**Sintoma:** a página abre, mas as chamadas à API respondem 502.

**Causa:** o Nginx do frontend guardou o endereço antigo do backend. O Compose
reinicia o frontend junto com o backend (`depends_on` com `restart: true`),
mas um `docker compose up -d backend` isolado pula essa regra.

**Correção:** `docker compose restart frontend`.

## Disco novo invisível para os contêineres

**Sintoma:** com `MEDIA_STORAGE_PATH` num disco instalado há pouco, os
contêineres não acham a pasta.

**Causa:** o Docker Desktop só enxerga os discos que existiam quando o WSL
iniciou.

**Correção:** `wsl --shutdown` e abra o Docker Desktop de novo.

## Acesso pela rede local não abre

**Sintoma:** `http://<IP da máquina>:3000` não responde de outro computador,
mas `http://localhost:3000` funciona na própria máquina.

**Causa:** o firewall do Windows bloqueia a porta 3000. Veja a regra em
[Publicar na internet](publicar-na-internet.md#pela-rede-local).

## Garage não sobe

**Sintoma:** com o perfil `s3`, o serviço `garage` reinicia sem parar.

**Causa:** falta `GARAGE_RPC_SECRET` no `.env` (o log diz `rpc_secret value is
missing`), ou a chave e o segredo não têm o formato exigido.

**Correção:** gere os valores como em [Armazenamento](armazenamento.md#s3-local-garage)
e aplique com `docker compose up -d`.

## Domínio bloqueado numa rede institucional

**Sintoma:** de dentro de uma rede de empresa ou de universidade, o endereço
público é bloqueado como *Newly Registered Domain*.

**Correção:** peça a recategorização ao fornecedor do filtro (veja
[Publicar na internet](publicar-na-internet.md#redes-que-bloqueiam-o-domínio)).
