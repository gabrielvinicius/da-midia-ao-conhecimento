# Primeiros passos

Neste tutorial você sobe o sistema inteiro numa máquina comum, sem placa de
vídeo, envia uma gravação curta e acompanha o resultado: transcrição, resumo,
capítulos, perguntas de revisão e busca pelo significado. Leva cerca de uma
hora, quase toda esperando o primeiro download dos modelos.

Ao final, você terá visto cada etapa do processamento acontecer e saberá onde
procurar quando quiser ir além.

> [!NOTE]
> Sem GPU, o processamento é várias vezes mais lento que na máquina de
> produção. Para este tutorial, use uma gravação de um a dois minutos.

## O que você precisa

- **Docker** com o Compose 2.24 ou mais recente (Docker Desktop no Windows ou
  no macOS, Docker Engine no Linux). Confira com `docker compose version`.
- **16 GB de memória** livres para o Docker: o worker de processamento pode
  usar até 12 GB.
- **Espaço em disco** para as imagens e os modelos (algumas dezenas de GB).
- **Git** e uma gravação curta em áudio ou vídeo (MP3, M4A, MP4...), de
  preferência em português.

## 1. Baixe o código e crie a configuração

```bash
git clone https://github.com/gabrielvinicius/da-midia-ao-conhecimento.git
cd da-midia-ao-conhecimento
cp .env.example .env
```

Abra o `.env` e preencha quatro valores:

```env
DB_PASSWORD=<uma senha qualquer para o banco local>
SECRET_KEY=<a chave gerada abaixo>
DEFAULT_ADMIN_EMAIL=voce@exemplo.com
DEFAULT_ADMIN_PASSWORD=<a sua senha>
```

Para gerar a `SECRET_KEY` (a API não inicia com o valor de exemplo nem com
menos de 32 caracteres):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

A senha do administrador precisa ter ao menos 8 caracteres, com letra
maiúscula, letra minúscula e número.

## 2. Suba o sistema

Use a variante sem GPU, que troca o PyTorch pela versão de CPU:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build
```

A primeira vez demora: o Docker constrói as imagens da aplicação e o serviço
`ollama-models` baixa o modelo de linguagem. Acompanhe o download:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml logs -f ollama-models
```

Quando ele terminar, confira se tudo está saudável:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml ps
```

Você deve ver `backend`, `frontend`, `worker-heavy`, `worker-light`,
`postgres`, `redis` e `ollama` com o estado `healthy`, e `migrate` e
`ollama-models` encerrados com código 0 (eles rodam uma vez e terminam).

## 3. Entre na plataforma

Abra <http://localhost:3000> e entre com o e-mail e a senha do administrador
que você colocou no `.env`. Você verá o **Painel**, ainda sem mídias.

> [!TIP]
> Depois de entrar, troque a senha pela interface (menu do usuário >
> Configurações) e apague `DEFAULT_ADMIN_PASSWORD` do `.env`.

## 4. Envie a gravação

1. Clique em **Enviar mídia**.
2. Arraste o arquivo para a área de envio ou clique para escolhê-lo.
3. Clique em **Enviar**. As **Opções avançadas** já vêm com o padrão do
   sistema.

O arquivo aparece no Painel com o estado **Processando**. Repare no sino, no
alto da página: os avisos chegam em tempo real, sem recarregar.

## 5. Acompanhe o processamento

A mídia passa por três estados, que você vê mudar no Painel:

1. **Processando**: o Whisper transcreve a fala e o modelo de visão descreve
   alguns quadros do vídeo.
2. **Analisando**: o texto é dividido em trechos, vetorizado e indexado para a
   busca; o modelo de linguagem identifica o tipo de conteúdo e escreve o
   resumo, os títulos dos capítulos e as perguntas de revisão.
3. **Concluído**: chega o aviso "Análise concluída. O resumo já está disponível."

Se quiser ver o trabalho por dentro, acompanhe o worker:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml logs -f worker-heavy
```

## 6. Explore o resultado

Abra a mídia pelo botão **Abrir**:

- **Resumo**: o texto gerado, com a verificação de fidelidade logo abaixo
  (quantas frases têm apoio na transcrição). Experimente **Corrigir resumo**:
  a versão da IA fica guardada.
- **Capítulos**, ao lado do reprodutor: clique num deles e o vídeo salta para
  aquele momento.
- **Estudo**: as perguntas de revisão, cada uma com o trecho de onde saiu.
- **Transcrição**: o texto com os horários; o botão de cada trecho leva o reprodutor até ele.
- **Baixar**: o resumo em Markdown, a transcrição em SRT ou WebVTT, ou tudo
  em JSON.

## 7. Busque pelo significado

Abra **Busca** e escreva uma pergunta sobre algo que foi dito na gravação,
**com outras palavras**. A busca compara significados, não palavras, e leva
direto ao momento da gravação em que o assunto aparece.

## 8. Desligue

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml down
```

Os dados ficam nos volumes do Docker e voltam na próxima vez que você subir o
sistema. Para apagar tudo, inclusive o banco e as mídias, acrescente `-v`.

## Próximos passos

- Conheça cada tela da plataforma: [Manual do usuário](../guias/manual-do-usuario.md)
  e [Manual do administrador](../guias/manual-do-administrador.md).
- Entenda o que aconteceu em cada etapa: [Pipeline de processamento](../explicacao/pipeline.md).
- Rode com GPU ou troque os modelos: [Modelos e etapas da análise](../guias/modelos-e-etapas.md).
- Coloque em produção: [Implantar em produção](../guias/implantar-em-producao.md).
- Contribua com o código: [Desenvolver](../guias/desenvolver.md).
