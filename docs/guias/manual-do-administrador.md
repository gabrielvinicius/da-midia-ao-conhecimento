# Manual do administrador

Este manual percorre as telas da área de administração: o resumo da
plataforma, a fila de processamento, as mídias e os usuários de todos, a
qualidade da IA, os tempos de cada etapa e o estado do servidor. O
administrador também usa todas as telas do [Manual do usuário](manual-do-usuario.md),
com as suas próprias mídias.

A instalação e a operação da máquina (implantação, cópias de segurança,
troca de modelos) estão nos [guias](../README.md#guias).

## Quem é administrador

- **O primeiro administrador** é criado na primeira inicialização, com o
  e-mail e a senha definidos em `DEFAULT_ADMIN_EMAIL` e
  `DEFAULT_ADMIN_PASSWORD` no `.env` (veja
  [Primeiros passos](../tutoriais/primeiros-passos.md)). Depois de entrar,
  troque a senha em **Configurações** e apague `DEFAULT_ADMIN_PASSWORD` do
  `.env`.
- **Os demais** são contas comuns promovidas por um administrador na tela
  [Usuários](#usuários).

Uma conta comum que tenta abrir um endereço da administração é levada de
volta ao próprio painel.

## Entrar na administração

Há três caminhos, todos visíveis só para administradores:

- o item **Administração** no menu lateral;
- o botão **Visão administrativa** no alto do painel;
- o menu do usuário > **Administração**.

A área tem o seu próprio menu lateral: **Resumo**, **Fila**, **Mídias**,
**Usuários**, **Qualidade da IA**, **Tempos** e **Servidor**. Para voltar às
telas comuns, use **Voltar ao meu painel**, no fim do menu, ou o menu do
usuário > **Meu painel**. A bolinha de conexão e a faixa de carga do servidor
funcionam como nas telas comuns.

## Resumo

É a primeira tela da administração e responde a duas perguntas: o que
acontece agora e o que pede atenção.

### Indicadores

Cada indicador é um link para a tela correspondente.

| Indicador | O que mostra | Leva a |
|---|---|---|
| **Usuários** | Total de contas e quantas estão ativas | [Usuários](#usuários) |
| **Mídias** | Total de mídias, as concluídas e a taxa de sucesso | [Mídias](#mídias) |
| **Na fila agora** | Mídias aguardando e em processamento | [Fila](#fila-de-processamento) |
| **Falhas em 24 h** | Falhas no período recente e o total de falhas | [Mídias](#mídias) |

Os indicadores **Na fila agora** e **Falhas** ficam destacados quando há mídia
parada ou falha recente.

### Prévia da fila

O quadro mostra as cinco mídias em andamento mais antigas, com a etapa
(**Aguardando**, **Transcrevendo** ou **Analisando**) e há quanto tempo estão
nela. **Ver fila** abre a fila completa.

### Alertas

O quadro **Alertas** informa a hora da última verificação e lista os
problemas encontrados, como mídias que parecem paradas e serviços sem
resposta. Sem problemas, mostra "Nenhum alerta no momento."

## Fila de processamento

A tela **Fila** mostra o trabalho em andamento. A GPU processa uma mídia por
vez, e as demais esperam na ordem de chegada; arquivos curtos passam à frente.
A tela se atualiza sozinha a cada 10 segundos, e o botão **Atualizar** força a
leitura.

### Contagens por etapa

| Etapa | O que está acontecendo |
|---|---|
| **Aguardando** | Enviada, esperando o worker |
| **Transcrevendo** | Transcrição, descrição dos quadros ou extração do texto |
| **Analisando** | Temas, resumo, capítulos e perguntas |

### Mídias em andamento

A lista vai da mídia mais antiga para a mais nova. Cada linha mostra:

1. a **posição** na fila;
2. o **nome**, que abre a página da mídia, e o tipo;
3. o **dono** e há quanto tempo a mídia foi enviada;
4. a **etapa atual** e há quanto tempo a mídia está nela;
5. a marca **Parece parada**, quando a mídia está na mesma etapa há mais
   tempo que o normal.

Com muitas mídias, a lista mostra só as mais antigas e avisa.

### O que fazer com uma mídia parada

1. Leia o aviso amarelo no alto da tela.
2. Confira se os workers estão rodando, na tela [Servidor](#servidor) ou com
   `docker compose logs worker-heavy` na máquina.
3. Abra a mídia e veja **Detalhes do processamento**.
4. Se o processamento não voltar, a própria plataforma marca como falha a
   análise que passa do prazo; a mídia pode então ser reprocessada na tela
   [Mídias](#mídias).

O guia [Solucionar problemas](solucionar-problemas.md) reúne as
causas já vistas e as correções.

### Tarefas no Celery

O quadro mostra quantas tarefas esperam um worker livre, em cada fila:

| Fila | Uso |
|---|---|
| **Transcrição (arquivos curtos, passam à frente)** | Gravações curtas |
| **Transcrição** | As demais gravações |
| **Análise e extração de texto** | Análise de todas as mídias e textos de documentos |
| **Manutenção (verificações periódicas)** | Tarefas automáticas de limpeza e recuperação |

"Não foi possível ler as filas no Redis" indica que o Redis não respondeu;
confira a tela [Servidor](#servidor).

## Mídias

A tela **Mídias** lista os envios de todos os usuários, para agir nos que têm
problema.

### Indicadores

- **Mídias listadas**: quantas correspondem à busca atual.
- **Em processamento**: transcrição ou análise em andamento, com o link **Ver
  fila**.
- **Concluídas** e **Falhas**, desde o início.

### Tabela

A tabela **Todas as mídias** vai da mais nova para a mais antiga, com as
colunas **Arquivo** (nome, tipo e tamanho), **Dono**, **Situação** e **Enviada
em**.

- O campo **Filtrar...** busca pelo nome.
- A paginação fica no rodapé da tabela.
- O nome do arquivo abre a página da mídia. O administrador vê e corrige a
  mídia de qualquer usuário como se fosse o dono.

### Ações de uma mídia

No menu de três pontos da linha:

- **Reprocessar**: só para mídias que falharam. A mídia volta para a fila, e
  os resultados anteriores dela são apagados.
- **Excluir mídia**: pede confirmação e apaga o arquivo, a transcrição e as
  análises. Não é possível desfazer.

### Reprocessar todas as falhas

1. Clique em **Reprocessar falhas**, no alto da tela. O botão fica desativado
   quando não há falhas.
2. Leia a confirmação: até 50 mídias voltam para a fila, uma de cada vez na
   GPU, e os resultados anteriores delas são apagados. Enquanto isso, os novos
   envios esperam mais.
3. Clique em **Reprocessar**, ou em **Cancelar**.

Antes de reprocessar em lote, vale entender por que as mídias falharam: se a
causa continuar (um modelo que não carrega, falta de memória), elas falham de
novo.

## Usuários

A tela **Usuários** lista as contas, com **E-mail**, **Papel** (Usuário ou
Administrador) e **Situação** (Ativa ou Desativada). O campo **Filtrar...**
busca pelo e-mail.

No menu de três pontos de cada conta:

- **Alterar papel**: abre a janela **Papel de ...**. Escolha **Usuário** ou
  **Administrador** no campo **Perfil** e clique em **Salvar**.
- **Desativar conta** / **Reativar conta**: a conta desativada perde o acesso
  já na próxima requisição, mas as mídias dela continuam guardadas. É o
  caminho para suspender alguém sem perder dados.
- **Excluir conta**: pede confirmação e apaga a conta com todas as mídias,
  transcrições, resumos e análises dela. Não é possível desfazer.

Ninguém desativa nem exclui a própria conta por esta tela: as duas opções
ficam desativadas na linha do administrador que está usando a tela.

## Qualidade da IA

A tela **Qualidade da IA** mede a qualidade pelo uso real: o que os usuários
precisaram corrigir e se acharam o resumo útil.

### Indicadores

| Indicador | O que mostra |
|---|---|
| **Análises** | Mídias com análise gravada |
| **Resumos úteis** | Porcentagem de avaliações positivas (polegar para cima) |
| **Resumos corrigidos** | Parcela das análises cujo resumo foi corrigido |
| **Trechos corrigidos** | Parcela dos trechos de transcrição corrigidos |

Quando há correção, mas ela arredonda para zero, a tela mostra "<1%", e não
"0%".

### Quadros

- **O que os usuários corrigiram**: uma barra para cada parte (resumo, títulos
  dos temas, capítulos, perguntas de revisão e transcrição), com a quantidade
  e a porcentagem. A versão da IA fica guardada na primeira correção, o que
  permite comparar as duas mais tarde.
- **O resumo foi útil?**: a divisão entre **Útil** e **Não foi útil** nas
  avaliações dadas pelo polegar, abaixo de cada resumo.
- **Comentários recentes**: os comentários deixados junto com a avaliação,
  quando existem, com a mídia e o veredito.
- **Análises corrigidas**: as mais recentes, com o que foi ajustado em cada
  uma. "Mídia excluída" indica que a mídia já não existe.

Uma parte muito corrigida aponta onde trocar o modelo ou ajustar a etapa vale
mais a pena (veja [Modelos e etapas da análise](modelos-e-etapas.md)).

## Tempos

A tela **Tempos de processamento** mostra quanto cada etapa levou nas mídias
já processadas, para estimar a fila e comparar modelos.

1. Escolha o período no seletor: **Últimos 7 dias**, **Últimos 30 dias** ou
   **Todo o período**.
2. Leia a tabela **Por etapa**, com uma linha por etapa e modelo:

| Coluna | Significado |
|---|---|
| **Tarefa** | A etapa (transcrição, descrição dos quadros, resumo...) |
| **Modelo** | O modelo usado |
| **Execuções** e **Falhas** | Quantas vezes a etapa rodou e quantas falhou |
| **Média**, **Mediana** e **Máximo** | Tempos da etapa |
| **Tempo real** | Tempo da etapa dividido pela duração da gravação |

Na coluna **Tempo real**, 0,50× significa que a etapa levou metade da duração
da gravação. São esses tempos que alimentam a previsão mostrada ao usuário na
página da mídia.

## Servidor

A tela **Servidor** mostra o uso da máquina e se cada serviço responde. Ela se
atualiza sozinha a cada 15 segundos, e o botão **Atualizar** força a leitura.
Ao lado do título, uma etiqueta resume a carga: **Carga normal**, **Carga
moderada**, **Carga alta** ou **Capacidade crítica**.

### Uso da máquina

Quatro cartões, com barra verde até 70%, âmbar até 90% e vermelha acima:

- **Memória da GPU**: o uso da placa inteira, em GB;
- **Uso da GPU**: a ocupação da placa pela transcrição, pela visão e pelo
  modelo de linguagem;
- **Processador**: a ocupação e o número de núcleos;
- **Memória**: a memória RAM usada e a total.

Sem leitura da GPU ("o worker pesado está parado?"), o worker que usa a placa
não está respondendo.

### Serviços

Cada serviço tem um ponto verde (**respondendo**) ou vermelho (**sem
resposta**):

| Serviço | Papel |
|---|---|
| **Banco de dados** | PostgreSQL com pgvector: dados, análises e busca |
| **Redis** | Fila de tarefas e avisos |
| **Ollama** | Modelo de linguagem (resumo, capítulos, perguntas) |
| **Workers do Celery** | Dois: o pesado (GPU: transcrição e análise) e o leve (verificações periódicas) |

O ponto dos workers fica verde só quando os dois respondem.

### Modelos carregados no Ollama

Lista os modelos de linguagem na memória da GPU neste momento. Eles ficam
carregados até 5 minutos depois do último uso e então são descarregados;
"Nenhum modelo na memória agora" é a situação normal com a fila vazia.

## Rotina sugerida

- **Todo dia**: abrir o **Resumo** e conferir os alertas e as falhas recentes.
- **Quando um usuário relata demora**: ver a **Fila** e o **Servidor**.
- **Quando há falhas**: abrir a mídia, ler os detalhes técnicos, corrigir a
  causa e só então usar **Reprocessar** ou **Reprocessar falhas**.
- **De tempos em tempos**: ver a **Qualidade da IA** e os **Tempos**, para
  decidir se vale trocar um modelo.
