# Segurança

As gravações de uma instituição podem conter dados pessoais, e a plataforma
fica aberta na internet. Esta página explica as defesas em cada camada: quem
entra, o que cada um vê, como a execução é isolada e como o código que chega à
produção é verificado.

## Dados que não saem da máquina

Todos os modelos (transcrição, visão, linguagem, vetores) rodam localmente.
Nenhuma gravação, transcrição ou resumo é enviado a um serviço externo, e não
há custo por uso. Essa é a restrição de projeto que orienta várias escolhas,
como o Ollama no lugar de uma API paga (ADR-011).

## Sessão e tokens

| Token | Onde trafega | Validade | Para quê |
|---|---|---|---|
| Acesso | Cabeçalho `Authorization` | 30 minutos | Toda chamada à API |
| Renovação | Cookie `httpOnly`, `SameSite=Lax` | 7 dias | Renovar o de acesso; **usado uma vez só** |
| Vídeo | URL do reprodutor | 6 horas, uma mídia | O `<video>` não manda cabeçalho |
| WebSocket | URL da conexão | 2 minutos | Abrir o canal de avisos |

- **O token de acesso nunca vai na URL.** Onde o navegador não manda
  cabeçalho (o vídeo e o WebSocket), entram tokens de finalidade restrita,
  pedidos em `POST /auth/scoped-token`, que só servem para aquela finalidade e
  aquele recurso.
- **A renovação gira a cada uso.** O token de renovação usado é consumido; uma
  cópia roubada só funciona uma vez, e o primeiro uso de quem a roubou
  invalida a sessão da vítima, que percebe ao ter de entrar de novo. O logout
  revoga o token no Redis.
- **O cookie não é lido por JavaScript** (`httpOnly`). Com HTTPS, ele só
  trafega cifrado (`USER_COOKIE_SECURE=true`).
- **Senhas** com bcrypt, e regras mínimas no cadastro (8 caracteres, com
  maiúscula, minúscula e número). Depois de 5 falhas por e-mail (ou 20 por
  IP), o login fica bloqueado por 15 minutos.
- **A chave que assina os tokens** (`SECRET_KEY`) é conferida ao iniciar: a API
  não sobe com o valor de exemplo nem com menos de 32 caracteres.
- **Sem revelar contas**: "Esqueci minha senha" e o reenvio da confirmação
  respondem igual com e sem conta cadastrada.

## Quem vê o quê

A regra é uma só, num lugar só (`shared/application/access.py`): **o dono ou
um administrador**. Os serviços de mídias, transcrições, análises e avisos a
aplicam, e as rotas nunca conferem o dono por conta própria.

Uma mídia de outra pessoa responde **404**, e não 403: a resposta não confirma
que o recurso existe. A busca filtra os trechos pelo dono na própria consulta
ao banco.

## Logs sem dados pessoais

Os logs não guardam e-mails nem o texto das buscas. Um e-mail aparece mascarado
e com um código (`g***@gmail.com#ffd7`), que permite reconhecer a mesma conta
em vários registros sem expor o endereço. As métricas do Prometheus nunca
levam o id de uma mídia ou de um usuário.

## Execução isolada

- **Portas expostas**: só a interface (3000) responde fora da máquina. A API
  (8000), o Prometheus e o Jaeger escutam só em `127.0.0.1`; o banco, o Redis,
  o Ollama e o Garage não publicam porta nenhuma.
- **Rede interna**: os serviços de dados ficam numa rede do Compose marcada
  como interna.
- **Contêineres sem privilégios**: nenhum pode ganhar privilégios novos
  (`no-new-privileges`). Os da aplicação rodam sem o usuário root e sem
  nenhuma *capability* do kernel; o Garage roda como root, mas também sem
  nenhuma.
- **Internet sem portas abertas**: o Cloudflare Tunnel parte da máquina para
  fora; nada fica escutando no roteador.

## Cadeia de suprimentos

O código que chega à produção passa por várias verificações (ADR-016):

- **Ações do GitHub fixadas pelo commit**, e não pelo nome da versão. Em março
  de 2026, quase todas as versões de uma ação de varredura passaram a apontar
  para código malicioso; só quem fixava o commit escapou.
- **Token mínimo** nos workflows: só leitura do repositório.
- **Workflows auditados** pelo zizmor e pelo actionlint.
- **Imagens varridas** pelo Trivy, que falha a CI com uma vulnerabilidade
  crítica que já tenha correção.
- **Dependências atualizadas** pelo Dependabot, cada uma pela CI
  ([Atualizar dependências](../guias/atualizar-dependencias.md)).
- **Versões fixas**: toda imagem do Compose tem versão ou digest, nunca
  `latest`; um teste confere.

## Limites conhecidos

- Não há autenticação em dois fatores nem login pela conta da instituição
  (SSO).
- Os segredos ficam no `.env` da máquina, protegido pelo sistema de arquivos,
  e não num cofre de segredos.
- A cópia de segurança fica na mesma máquina até haver o repositório remoto
  ([Operação](operacao.md#limites-conhecidos)).

## Veja também

- [Publicar na internet](../guias/publicar-na-internet.md): HTTPS e o cookie
  seguro.
- [Referência da API](../referencia/api.md): o acesso exigido por cada rota.
