# Publicar na internet

Dois jeitos de chegar ao sistema de outros computadores: pela **internet, com
HTTPS**, por um túnel da Cloudflare, ou pela **rede local**, por HTTP na porta
3000. Os dois podem funcionar ao mesmo tempo.

## Pela internet, com o Cloudflare Tunnel

O túnel parte da própria máquina para a Cloudflare. Nenhuma porta é aberta no
roteador, funciona atrás do NAT da operadora, e a Cloudflare emite e renova o
certificado HTTPS.

1. No painel da Cloudflare, em **Zero Trust > Networks > Tunnels**, crie um
   túnel do tipo *Cloudflared* e copie o token.
2. Em **Public Hostname**, aponte o seu domínio (por exemplo,
   `tcc.seudominio.dev`) para o serviço `http://frontend:80`. É o nome do
   contêiner da interface na rede do Compose, não `localhost`.
3. No `.env` da produção:

   ```env
   CLOUDFLARE_TUNNEL_TOKEN=<token do túnel>
   COMPOSE_PROFILES=internet
   PUBLIC_URL=https://tcc.seudominio.dev
   USER_COOKIE_SECURE=true
   ```

   Se o perfil `s3` também estiver ligado, use `COMPOSE_PROFILES=internet,s3`.
4. Aplique com `docker compose up -d` (ou pela implantação seguinte) e
   confira: `https://tcc.seudominio.dev/api/health` responde `200`.

> [!NOTE]
> O `deploy.ps1` avisa quando há um token no `.env` mas o perfil `internet`
> está desligado: antes, o túnel ficava fora do ar sem nenhuma mensagem.

### Mais de um endereço

O mesmo túnel atende vários hostnames. Cada um é mais uma linha em **Public
Hostname**; o Cloudflare cria o registro de DNS junto.

| Endereço | Serviço | Proteção |
|---|---|---|
| `tcc.seudominio.dev` | `http://frontend:80` | Login da própria plataforma |
| `app.seudominio.dev` | `http://frontend:80` | Login da própria plataforma |
| `docs.seudominio.dev` | `http://docs:80` | Nenhuma: o site é público |
| `metricas.seudominio.dev` | `http://prometheus:9090` | Cloudflare Access |
| `rastros.seudominio.dev` | `http://jaeger:16686` | Cloudflare Access |

A interface e a API respondem pela mesma origem: um endereço novo da
plataforma não pede mudança no CORS nem no `.env`. O `PUBLIC_URL` continua
um só, porque é o endereço dos links enviados por e-mail. A sessão fica
separada por endereço: quem entrou por um precisa entrar de novo no outro.

### Painéis com o Cloudflare Access

O Prometheus e o Jaeger não têm login, e os rastros incluem dados das
requisições. Na internet, eles ficam atrás do Cloudflare Access, que pede um
código enviado ao e-mail autorizado antes de qualquer requisição chegar à
máquina.

1. Em **Zero Trust > Access > Applications**, crie uma aplicação
   *Self-hosted* para cada endereço, com uma política *Allow* que inclua só
   os e-mails autorizados. O login por código no e-mail (*One-time PIN*)
   dispensa outro provedor de identidade.
2. **Crie a aplicação antes do hostname público.** Na ordem inversa, o
   endereço fica aberto durante esse intervalo.
3. No hostname público, em **Additional application settings > Access**,
   ligue **Protect with Access** com a etiqueta (AUD) da aplicação. O
   próprio `cloudflared` passa a recusar requisições sem o token do Access,
   mesmo que alguém mude o DNS por engano.

Sem login, o endereço responde com um redirecionamento (302) para a página
de entrada do Access:

```bash
curl -sI https://metricas.seudominio.dev/ | head -1   # HTTP/2 302
```

### Site da documentação

O serviço `docs` só existe com o perfil `internet`: a implantação constrói
o site a cada versão (`docker/docs.Dockerfile`, em modo estrito), junto com
a interface. O site é público, como o repositório: nada do que entra em
`docs/` pode depender de ficar escondido.

### Redes que bloqueiam o domínio

Filtros de rede de empresas e instituições (por exemplo, o FortiGuard) costumam
bloquear domínios registrados há pouco tempo, na categoria *Newly Registered
Domain*. Peça a recategorização no site do fornecedor do filtro, indicando a
categoria *Education*; a análise leva alguns dias.

## Pela rede local

A interface responde por HTTP na porta 3000 de todas as interfaces da máquina
(`http://<IP da máquina>:3000`). No Windows, o firewall bloqueia o acesso
vindo de outros computadores até haver uma regra para a porta. Num PowerShell
**como administrador**:

```powershell
New-NetFirewallRule -DisplayName "Da Mídia ao Conhecimento - rede local" `
  -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow `
  -Profile Private -RemoteAddress LocalSubnet
```

A regra vale só para redes marcadas como **privadas** e para endereços da
própria sub-rede.

> [!WARNING]
> Com `USER_COOKIE_SECURE=true` (necessário com HTTPS), o navegador descarta o
> cookie da sessão quando o acesso é por HTTP. Pela rede local, o login
> funciona, mas a sessão não sobrevive a um recarregamento da página. Para
> usar as duas formas de acesso, prefira o endereço HTTPS também dentro da
> rede local.

## Ollama para outros programas

O Ollama do compose não publica porta: só a API e os workers o usam. Para
outros programas (de outra máquina da rede ou pela internet) usarem os mesmos
modelos, o serviço opcional `ollama-gateway` abre o acesso com um token. O
Ollama não tem autenticação própria; o gateway recusa (401) as requisições
sem o cabeçalho `Authorization: Bearer <token>`. A API e os workers continuam
indo direto ao Ollama, sem passar por ele.

1. No `.env`, gere o token e inclua o perfil `ollama-api`:

    ```bash
    python -c "import secrets; print(secrets.token_urlsafe(48))"
    ```

    ```ini
    OLLAMA_API_TOKEN=<o token gerado>
    COMPOSE_PROFILES=internet,ollama-api
    ```

2. Suba o gateway (os demais serviços não são recriados):

    ```bash
    docker compose up -d --no-deps ollama-gateway
    ```

3. Pela rede local, libere a porta 11435 (PowerShell como administrador):

    ```powershell
    New-NetFirewallRule -DisplayName "Ollama API (gateway com token) 11435" `
      -Direction Inbound -Protocol TCP -LocalPort 11435 -Action Allow `
      -Profile Private -RemoteAddress LocalSubnet
    ```

4. Pela internet, adicione no túnel um hostname público (por exemplo
   `ollama.seudominio`) apontando para `http://ollama-gateway:8080`.

Os programas usam `http://<ip da máquina>:11435` ou `https://ollama.seudominio`
com o token. Clientes no formato da OpenAI usam o caminho `/v1` e o token como
chave da API:

```bash
curl https://ollama.seudominio/api/chat \
  -H "Authorization: Bearer <token>" \
  -d '{"model":"qwen3.5:9b","messages":[{"role":"user","content":"oi"}]}'
```

> [!WARNING]
> O Ollama mantém um modelo carregado por vez (`OLLAMA_MAX_LOADED_MODELS=1`).
> Pedidos de fora dividem a GPU com as análises: um modelo diferente do
> `LLM_MODEL` faz o Ollama trocar de modelo, e as análises em andamento
> esperam a troca. Pela Cloudflare, respostas sem streaming que levam mais de
> 100 s terminam em erro 524; use `"stream": true`.

Para trocar o token, edite o `.env` e recrie o gateway com o comando do passo 2.

## Veja também

- [Segurança](../explicacao/seguranca.md): por que o cookie da sessão é
  `httpOnly` e só trafega cifrado.
- [Solucionar problemas](solucionar-problemas.md#endereço-público-responde-530):
  o endereço público responde 530.
