# Manual do usuário

Este manual percorre, tela por tela, tudo o que uma pessoa com conta comum faz
na plataforma: criar a conta, enviar arquivos, acompanhar o processamento,
estudar o resultado e corrigir o que a IA errou. As telas exclusivas do
administrador estão no [Manual do administrador](manual-do-administrador.md).

Os nomes entre aspas e em negrito são os que aparecem na interface.

## Visão geral da interface

Depois de entrar, toda tela tem três partes:

- **Menu lateral** (no celular, uma faixa de atalhos abaixo do cabeçalho):
  **Painel**, **Envios**, **Busca**, **Revisão**, **Resumos**, **Temas** e
  **Como funciona**. O botão com três traços, no alto do menu, recolhe o menu
  e deixa só os ícones.
- **Cabeçalho**, à direita:
  - a **bolinha de conexão**: verde quando os avisos em tempo real estão
    chegando, amarela enquanto reconecta, vermelha sem conexão. Sem conexão,
    a plataforma funciona normalmente, mas os avisos só aparecem ao recarregar
    a página;
  - o **sino** de avisos (veja [Avisos](#avisos));
  - o **menu do usuário** (ícone de pessoa), com o seu e-mail,
    **Configurações** e **Sair**.
- **Faixa de carga do servidor**, acima do cabeçalho, que só aparece quando a
  máquina está ocupada: **Carga Moderada** (os próximos processamentos podem
  demorar), **Alta carga** (novos processamentos esperam na fila) ou
  **Capacidade crítica** (o processamento atual pode falhar e ser repetido
  automaticamente). Ela é só informativa; não é preciso fazer nada.

## Criar a conta e entrar

### Cadastro

1. Na tela **Entrar**, clique em **Cadastre-se**.
2. Na tela **Criar conta**, informe o e-mail e uma senha com pelo menos 8
   caracteres, com letra maiúscula, letra minúscula e número.
3. Clique em **Criar conta**.

O que acontece depois depende de a instalação enviar e-mails:

- **Com envio de e-mails**, a tela **Confirme seu e-mail** pede que você abra
  o link enviado, válido por 24 horas. Se ele não chegar, confira a caixa de
  spam ou clique em **Reenviar o link**. Ao abrir o link, a tela
  **Confirmação de e-mail** mostra "E-mail confirmado. Sua conta está ativa." e
  o botão **Entrar**.
- **Sem envio de e-mails**, a conta já fica ativa, e a plataforma volta para a
  tela de login com a mensagem "Cadastro realizado".

### Login

1. Na tela **Entrar**, informe o e-mail e a senha.
2. Clique em **Entrar**. Você chega ao [Painel](#painel).

Situações comuns:

- **Conta ainda não confirmada**: um quadro amarelo avisa e oferece
  **Reenviar o link de confirmação**.
- **Muitas tentativas erradas**: depois de algumas senhas incorretas seguidas,
  o login fica bloqueado por alguns minutos, como proteção. Espere e tente de
  novo.
- **Conta desativada**: o administrador suspendeu o acesso; fale com ele.

### Esqueci minha senha

O link **Esqueci minha senha** só aparece quando a instalação envia e-mails.

1. Na tela **Entrar**, clique em **Esqueci minha senha**.
2. Informe o e-mail da conta e clique em **Enviar o link**. A resposta é a
   mesma exista a conta ou não, para não revelar quem está cadastrado.
3. Abra o link recebido. Ele vale por 1 hora e uma única vez.
4. Na tela **Nova senha**, digite a nova senha duas vezes e clique em
   **Salvar a nova senha**.
5. Na tela **Senha alterada**, clique em **Entrar**.

Se o link tiver expirado ou já tiver sido usado, a tela oferece **Pedir um
novo link**.

## Painel

É a tela inicial. Mostra as suas mídias e o andamento de cada uma.

### Primeira visita

Sem nenhuma mídia, o painel mostra só o cartão **Envie sua primeira mídia** e
o botão **Enviar mídia**, que leva aos [Envios](#enviar-mídias).

### Indicadores

No alto ficam três indicadores, que também funcionam como filtros:

| Indicador | O que mostra | Ao clicar |
|---|---|---|
| **Mídias** | Total, com quantos vídeos, áudios e textos | Mostra todas |
| **Concluídas** | Mídias prontas e a porcentagem do total | Filtra as concluídas |
| **Com falha** | Mídias que falharam (em vermelho quando há alguma) | Filtra as que falharam |

### Lista de mídias

O quadro **Suas mídias** lista os envios, dos mais novos para os mais antigos.

- **Buscar pelo nome**: filtra pelo nome do arquivo enquanto você digita. O
  **X** limpa a busca.
- **Atualizar lista** (seta circular): recarrega a lista.
- **Filtros**: **Todas**, **Em andamento**, **Concluídas** e **Com falha**,
  cada um com a quantidade. Quando nada corresponde, o botão **Limpar
  filtros** volta à lista completa.
- **Paginação**, no rodapé: escolha 10, 25 ou 50 por página e use as setas
  para avançar ou voltar.

Cada linha mostra o nome, o tipo, há quanto tempo foi enviada, o tamanho e a
situação:

| Situação | Significado |
|---|---|
| **Enviado** | O arquivo chegou e espera a vez na fila |
| **Processando** | Transcrição da fala, descrição dos quadros ou extração do texto |
| **Analisando** | Resumo, capítulos, perguntas, temas e indexação para a busca |
| **Concluído** | Tudo pronto |
| **Falhou** | Algo deu errado; o motivo aparece em vermelho, em linguagem simples |

Ações de cada linha:

- **Abrir**: leva à [página da mídia](#página-da-mídia).
- **Tentar novamente**: só nas mídias que falharam; coloca a mídia de novo
  na fila.
- **Menu de três pontos** > **Excluir mídia**: pede confirmação e apaga o
  arquivo e tudo o que foi gerado a partir dele. Não é possível desfazer.

## Enviar mídias

A tela **Enviar mídias** (menu **Envios**, ou o botão **Enviar mídia** do
painel) recebe um ou vários arquivos de uma vez.

### Passo a passo

1. Arraste os arquivos para a área tracejada ou clique nela para escolhê-los.
2. Confira a lista que aparece abaixo da área. Cada arquivo mostra o tipo
   reconhecido e o tamanho. Para tirar um arquivo da lista, clique no **X** ao
   lado dele.
3. Clique em **Enviar** (ou **Enviar N mídias**, com vários arquivos).
4. Acompanhe a barra de progresso de cada arquivo. Os arquivos sobem um por
   vez.
5. Ao final, o quadro verde confirma o envio. Clique em **Ver no painel** ou
   em **Enviar outros**. Cada arquivo enviado também ganha o link **Abrir**.

O envio termina em instantes. A transcrição e a análise continuam no servidor,
e você pode fechar a página: o sino avisa quando cada uma termina.

### Arquivos aceitos

| Tipo | Formatos | O que a plataforma faz |
|---|---|---|
| Vídeo | MP4, WebM, MOV, AVI, MKV, FLV | Transcreve a fala e descreve o que aparece na tela |
| Áudio | MP3, WAV, M4A, FLAC, AAC, OGG | Transcreve a fala, com o horário de cada trecho |
| Documento ou imagem | PDF, DOCX, TXT, PNG, JPG, TIFF, BMP | Extrai o texto, com leitura de imagem (OCR) nos escaneados |

Cada arquivo pode ter até 500 MB. Arquivos grandes sobem em partes: se a
conexão cair, só a parte interrompida é repetida. Um arquivo de tipo não
aceito ou grande demais aparece na lista com o motivo em vermelho e não é
enviado. Quando o envio de um arquivo falha, o botão com a seta circular, ao
lado dele, tenta de novo.

### Opções avançadas

O quadro recolhido **Opções avançadas** já vem com o padrão do sistema, e na
maior parte das vezes não precisa ser aberto:

- **Onde guardar os arquivos**: o armazenamento usado pela instalação.
- **Modelo de transcrição (vídeos e áudios)**: **Automático** escolhe o
  modelo conforme a máquina; as outras opções, quando existem, forçam um
  modelo específico.

### Para um resultado melhor

- Prefira gravações com o microfone perto de quem fala e pouco ruído.
- Envie PDFs com texto selecionável sempre que possível: o OCR de documentos
  escaneados é mais lento e erra mais.
- Envie uma aula ou reunião por arquivo, para que o resumo e os capítulos
  fiquem mais claros.

Como referência, uma aula em vídeo de 30 minutos fica pronta em cerca de
4 minutos, se não houver outras mídias na fila. O servidor processa uma mídia
por vez.

## Página da mídia

Aberta pelo botão **Abrir** do painel, pelo aviso de conclusão ou por um
resultado da busca. Ela se organiza em cabeçalho, coluna do reprodutor e
abas.

### Cabeçalho

- **Título**: o título do resumo, quando a análise já terminou; o nome do
  arquivo aparece logo abaixo.
- **Etiquetas**: situação, tipo de conteúdo identificado (Aula, Palestra,
  Opinião / ensaio, Reunião, Entrevista / podcast, Tutorial ou Documento),
  tipo de arquivo, duração e data do envio.
- **Frases conferidas**: por exemplo "18/20 frases conferidas · 2 a revisar".
  É o resultado da verificação automática do resumo contra a transcrição.
  Clicar leva à aba **Resumo**.
- **Detalhes do processamento**: abre uma janela com a situação de cada etapa
  (envio, transcrição, análise), o tempo que cada etapa da análise levou, o
  dispositivo usado (GPU ou CPU) e se o resumo veio do modelo principal, do
  modelo reserva ou de um resumo simplificado.
- **Baixar**: veja [Baixar e imprimir](#baixar-e-imprimir).

Enquanto a mídia está na fila ou em processamento, um quadro mostra a
**previsão de tempo**, calculada pela velocidade dos processamentos anteriores
nesta instalação. Ele não aparece quando ainda não há base para estimar.

Quando a mídia falhou, um quadro vermelho explica o motivo e o botão
**Reprocessar**, no alto, coloca a mídia de novo na fila. Em **Detalhes
técnicos** fica a mensagem original do erro, útil para o administrador.

### Coluna do reprodutor

Em vídeos e áudios, a coluna da esquerda acompanha a rolagem da página e
reúne:

- o **reprodutor** do vídeo ou do áudio;
- os **Capítulos**, com uma linha do tempo em que a largura de cada capítulo
  corresponde à sua duração. O capítulo em reprodução fica destacado; clicar
  em um capítulo leva o reprodutor ao início dele;
- o **Tom ao longo da gravação**, uma faixa colorida (verde positivo, cinza
  neutro, vermelho negativo). Clicar em um ponto leva ao trecho.

Nos documentos não há reprodutor; os horários dão lugar à ordem do texto.

### Aba Resumo

1. Leia o resumo, organizado por assunto.
2. Confira o quadro de **verificação de fidelidade**, logo abaixo:
   - verde quando todas as frases verificadas têm apoio na transcrição;
   - amarelo quando há algo a conferir. Abra **Frases sem trecho parecido na
     gravação** (com o horário do trecho mais próximo), **Partes da gravação
     que o resumo não menciona** (clicar no intervalo leva o reprodutor até
     ele) e **Números a conferir**;
   - um aviso de **resumo incompleto** quando o modelo parou antes do fim.

   A verificação compara significados. Ela aponta assuntos que não estão na
   gravação, mas não percebe, por exemplo, um nome trocado.
3. Avalie o resumo em **Este resumo foi útil?**, com o polegar para cima ou
   para baixo. A avaliação alimenta o relatório de qualidade do administrador.
4. Para corrigir, clique em **Corrigir resumo**:
   1. edite o texto à esquerda, em Markdown (`#` título, `##` seção, `-` item,
      `**negrito**`), e acompanhe a pré-visualização à direita;
   2. clique em **Salvar correção** (ou **Cancelar**).

   A versão da IA fica guardada. Depois da correção, a faixa **Resumo
   corrigido por você** oferece **Ver versão da IA** e **Ver versão
   corrigida**, para comparar as duas.

Um resumo corrigido não é substituído se a análise for refeita.

### Aba Estudo

Mostra as **perguntas de revisão** geradas a partir do conteúdo, com a
quantidade no nome da aba.

- **Mostrar resposta** revela a resposta e o horário em que ela aparece na
  gravação; clicar no horário leva o reprodutor até lá. **esconder** oculta a
  resposta de novo.
- **Testar-me** mostra uma pergunta por vez: pense na resposta, clique em
  **Revelar resposta** e depois em **Próxima pergunta**. **Ver todas** volta à
  lista.
- **Editar capítulos e perguntas** abre o editor:
  1. corrija os **Títulos dos capítulos** (os horários de início não mudam);
  2. em **Perguntas de revisão**, altere pergunta, resposta e momento da
     resposta (no formato `mm:ss`), remova uma pergunta pela lixeira ou
     acrescente outra com **Adicionar pergunta**;
  3. clique em **Salvar**. O botão só fica ativo quando todas as perguntas
     têm pergunta e resposta e os horários estão no formato certo.

Gravações curtas e alguns documentos não têm capítulos nem perguntas; a aba
informa quando é o caso. Para estudar as perguntas de todas as mídias juntas,
use a [Revisão](#revisão).

### Aba Transcrição (ou Texto extraído)

Nos vídeos e áudios, a aba se chama **Transcrição**; nos documentos, **Texto
extraído**.

- Cada trecho tem o horário de início. Clicar no horário leva o reprodutor
  até ele.
- O trecho em reprodução fica destacado, e a lista rola junto com o vídeo
  enquanto **Acompanhar o vídeo** estiver marcado. Desmarque para ler com
  calma sem que a lista se mova.
- **Buscar na transcrição** filtra os trechos que contêm a palavra, sem
  diferenciar acentos e maiúsculas, e destaca as ocorrências.
- Para **corrigir um trecho**:
  1. clique no lápis ao lado dele;
  2. ajuste o texto (o texto original da IA aparece logo abaixo, para
     referência);
  3. clique em **Salvar** (ou **Cancelar**).

  O trecho ganha a marca **corrigido**, e a contagem no alto da aba informa
  quantos trechos você corrigiu. A próxima análise da mídia usa o texto
  corrigido.

### Aba Temas e tom

- **Temas**, na ordem em que aparecem: cada um com o horário de início, o
  título, a parcela do conteúdo que ocupa, um trecho representativo e as
  palavras-chave. Para corrigir um título, clique no lápis, digite e confirme
  com o visto ou com Enter (Esc cancela). O tema corrigido ganha a marca
  **corrigido**, e o título da IA fica guardado.
- **Tom**: o tom predominante, a quantidade de trechos positivos, neutros e
  negativos e a faixa ao longo da gravação. O modelo de tom foi treinado com
  textos de redes sociais; em aulas e ensaios, "negativo" costuma indicar uma
  crítica ou um alerta, e não uma emoção.

Quando o administrador desligou a análise de temas ou de tom, a aba informa
que ela não foi feita nesta mídia.

### Aba Na tela

Só aparece em vídeos com quadros descritos. Lista o que aparecia na tela
(slides, títulos, nomes) em alguns momentos do vídeo, com o horário de cada
um. Essas descrições também servem de contexto para o resumo.

### Baixar e imprimir

O botão **Baixar**, no cabeçalho, monta os arquivos no próprio navegador:

| Grupo | Opção | Arquivo |
|---|---|---|
| Resumo e estudo | **Resumo** | Markdown (`.md`) |
| Resumo e estudo | **Guia de estudo completo** | Resumo, capítulos, perguntas e temas (`.md`) |
| Transcrição | **Texto com horários** | Texto (`.txt`) |
| Transcrição | **Legendas SRT** | Para reprodutores e editores de vídeo (`.srt`) |
| Transcrição | **Legendas WebVTT** | Para páginas web (`.vtt`) |
| Dados | **Tudo em JSON** | Todos os dados, para outras ferramentas (`.json`) |

**Imprimir ou salvar em PDF** imprime o resumo e o guia de estudo; para obter
o PDF, escolha "Salvar como PDF" na janela de impressão do navegador. As
opções sem conteúdo ainda (por exemplo, legendas de um documento) ficam
desativadas.

## Busca

A **Busca** encontra trechos pelo significado em todas as suas mídias já
analisadas, mesmo que as palavras da pergunta não tenham sido ditas.

1. Escreva uma pergunta ou descreva o assunto, com pelo menos 3 caracteres.
   Exemplo: "em qual aula expliquei a regra da cadeia?".
2. Clique em **Buscar** ou tecle Enter.
3. Leia os resultados, agrupados por mídia. Cada trecho mostra:
   - o intervalo de tempo na gravação;
   - o grau de relação com a pergunta: **Trata disso**, **Relacionado**,
     **Pode ter relação** ou **Pouca relação**;
   - o texto do trecho, com as palavras da pergunta destacadas.
4. Clique em **Abrir neste momento** para abrir a mídia já no instante do
   trecho, com a aba da transcrição aberta. Nos documentos, o link se chama
   **Abrir a mídia**.

Cada mídia mostra os três melhores trechos; **Mais N trechos desta mídia**
mostra os demais.

Antes da primeira busca, a tela mostra dicas e exemplos clicáveis. As
**Buscas recentes** ficam guardadas só neste navegador; o **X** ao lado de uma
delas a esquece.

Quando nenhum trecho trata claramente da pergunta, um aviso amarelo informa e
a lista mostra os mais próximos, para você conferir. Se a busca não encontrar
nada, tente outras palavras ou uma pergunta mais específica. Mídias ainda em
processamento só entram na busca quando a análise termina.

## Revisão

A **Revisão** reúne as perguntas de todas as suas mídias, com revisão
espaçada: o que você acerta volta mais tarde, e o que erra volta logo.

### Indicadores

| Indicador | O que conta |
|---|---|
| **Para revisar** | Perguntas novas e as que chegaram na data de revisão |
| **Dominadas** | Perguntas acertadas várias vezes seguidas |
| **Aprendendo** | Perguntas já respondidas e ainda não dominadas |
| **Acertos** | Porcentagem de acertos entre todas as respostas marcadas |

### Como estudar

1. Escolha **Para revisar** (só o que está na hora) ou **Todas**.
2. Se quiser, filtre por uma mídia no seletor **Todas as mídias** e clique em
   **Embaralhar** para mudar a ordem.
3. Leia a pergunta e responda de cabeça.
4. Clique em **Mostrar resposta**. Se quiser conferir na fonte, clique em
   **Ver na gravação**, que abre a mídia no momento da resposta.
5. Marque **Acertei** ou **Errei**.

Cada pergunta mostra a sua situação: **Nova**, **Revisar agora**, **Revisar
em ...** ou **Dominada**. Acertos seguidos afastam a próxima revisão para 1,
3, 7 e 14 dias; um erro traz a pergunta de volta no mesmo dia e recomeça a
contagem. A partir do terceiro acerto seguido, a pergunta conta como
dominada.

Quando não há nada para revisar, a tela oferece **Ver todas as perguntas**,
para praticar mais.

## Resumos

A tela **Resumos** é um caderno com os resumos de todas as suas mídias, para
ler em sequência.

- Cada resumo mostra o nome da mídia (que é um link para ela), o tipo de
  conteúdo, a quantidade de capítulos e de perguntas e os temas.
- **Ler tudo** abre o resumo inteiro; **Recolher** volta à prévia.
- **Buscar nos resumos** filtra pelo nome da mídia, pelos temas e pelo texto.
- **Baixar** gera o caderno em **PDF**, para ler, imprimir ou enviar, ou em
  **Markdown (.md)**, para editar em outro aplicativo. O arquivo contém os
  resumos que estão na tela, respeitando a busca.
- **Imprimir** imprime só os resumos, sem os menus.

## Temas

A tela **Temas** junta os assuntos de todas as suas mídias pelo título.

- Os temas que aparecem em mais de uma mídia vêm primeiro, com a marca **em N
  mídias**: é onde as aulas se conectam.
- Cada tema lista as mídias em que aparece, com o horário (clicar abre a
  mídia naquele momento), um trecho representativo e as palavras-chave.
- **Buscar tema ou palavra-chave** filtra a lista.
- Os filtros **Todos** e **Em mais de uma mídia** mostram a quantidade de
  cada grupo.

## Avisos

A plataforma avisa quando cada etapa termina ou falha.

### Sino

O sino, no cabeçalho, ganha um ponto quando há avisos não lidos.

1. Clique no sino para ver os avisos mais recentes.
2. Clique em um aviso para marcá-lo como lido, ou em **Marcar todos como
   lidos**.
3. **Ver todos os avisos** abre a tela de avisos.

### Tela de avisos

A tela **Avisos** guarda o histórico completo.

- Os filtros **Todos** e **Não lidos** escolhem o que aparece.
- Cada aviso tem um ícone: verde para o que terminou, vermelho para o que
  falhou (com o motivo em linguagem simples) e azul para as demais
  informações.
- **Abrir mídia** leva à página da mídia do aviso.
- Clicar em um aviso o marca como lido; **Marcar todos como lidos** marca
  todos de uma vez.

## Como funciona

A tela **Como funciona** (no celular, **Ajuda**) resume, em seções que abrem e
fecham, o que a plataforma faz com cada arquivo, os formatos e limites, o
tempo de processamento, o que há na página da mídia, como corrigir a IA, como
funcionam a revisão, os resumos e os temas, o que fazer quando algo falha e
como os dados são tratados.

## Configurações

Aberta pelo menu do usuário > **Configurações**.

Para trocar a senha:

1. Informe a **Senha atual**.
2. Digite a **Nova senha** (pelo menos 8 caracteres) e repita em **Confirme a
   nova senha**.
3. Clique em **Trocar senha**.

Por segurança, depois da troca é preciso entrar de novo com a nova senha.

## Sair

No menu do usuário, clique em **Sair**. A sessão é encerrada também no
servidor, e entrar de novo exige o e-mail e a senha.

## Quando algo falha

- **A mídia ficou como Falhou**: leia o motivo na linha do painel ou no
  quadro vermelho da página da mídia e clique em **Tentar novamente** (painel)
  ou **Reprocessar** (página da mídia). Se falhar de novo, avise o
  administrador e informe o nome do arquivo.
- **Uma parte da análise falhou** (o tom, por exemplo): o restante continua
  disponível, e a janela **Detalhes do processamento** mostra qual etapa
  faltou.
- **A mídia está há muito tempo na mesma situação**: com outras mídias na
  fila, a sua espera a vez. A faixa de carga, quando aparece, indica que o
  servidor está ocupado.
- **Os avisos não chegam**: confira a bolinha de conexão no cabeçalho. Se
  estiver vermelha, recarregue a página.
- **Endereço inexistente**: a tela **Página não encontrada** oferece o caminho
  de volta.

## Privacidade

Os arquivos são processados no próprio servidor da instalação, sem serviços
externos de IA. Só você vê as suas mídias; os administradores também podem
abri-las, para resolver problemas.
