# Documentação

**Da Mídia ao Conhecimento** transforma aulas gravadas, áudios e documentos em
material de estudo: transcreve, descreve o que aparece na tela, resume conforme
o tipo de conteúdo, divide a gravação em capítulos, propõe perguntas de revisão
e permite buscar trechos pelo significado em todo o acervo. Tudo roda numa
única máquina, sem enviar os dados para fora.

Esta documentação segue o [Diátaxis](https://diataxis.fr/): cada página tem
um único propósito, e as quatro seções abaixo respondem a necessidades
diferentes. Comece pela que corresponde ao que você precisa agora.

| Você quer... | Vá para |
|---|---|
| **aprender** a usar e rodar o sistema pela primeira vez | [Tutorial](#tutorial) |
| **resolver** uma tarefa concreta (implantar, restaurar, trocar um modelo) | [Guias](#guias) |
| **consultar** um detalhe exato (rota da API, variável, evento) | [Referência](#referência) |
| **entender** como e por que o sistema funciona assim | [Explicação](#explicação) |

## Tutorial

- [Primeiros passos](tutoriais/primeiros-passos.md): sobe o sistema numa
  máquina sem GPU, envia uma gravação curta e acompanha o resultado do começo
  ao fim.

## Guias

Para quem já conhece o sistema e tem uma tarefa a cumprir.

| Guia | Quando usar |
|---|---|
| [Implantar em produção](guias/implantar-em-producao.md) | Preparar a máquina, o runner e a implantação contínua |
| [Publicar na internet](guias/publicar-na-internet.md) | HTTPS pelo Cloudflare Tunnel, ou acesso pela rede local |
| [Cópias de segurança](guias/copias-de-seguranca.md) | Configurar, conferir e restaurar as cópias |
| [Armazenamento](guias/armazenamento.md) | Mídias em outro disco, S3 local (Garage) ou serviço S3 externo |
| [Modelos e etapas da análise](guias/modelos-e-etapas.md) | Trocar o modelo de linguagem ou de transcrição, ligar e desligar etapas, variantes de GPU |
| [Desenvolver](guias/desenvolver.md) | Ambiente local, testes, verificações da CI e regras do código |
| [Atualizar dependências](guias/atualizar-dependencias.md) | Tratar os PRs do Dependabot e as versões maiores |
| [Solucionar problemas](guias/solucionar-problemas.md) | Sintoma, causa e correção dos incidentes já vistos |

## Referência

Descrições exatas, para consulta. As três primeiras são **geradas a partir do
código** (`scripts/docs/gerar_referencia.py`), e um teste falha quando ficam
desatualizadas.

| Página | Conteúdo |
|---|---|
| [API](referencia/api.md) | Todas as rotas, com o acesso exigido |
| [Configuração](referencia/configuracao.md) | Todas as variáveis de ambiente, com o padrão e a descrição |
| [Eventos e filas](referencia/eventos-e-filas.md) | Eventos de integração (quem publica e quem reage), tarefas e filas |
| [Modelos de IA](referencia/modelos.md) | Modelo de cada etapa, com tempos e memória medidos |
| [Comandos](referencia/comandos.md) | Scripts de operação, verificações e tarefas do dia a dia |
| [Estrutura do repositório](referencia/estrutura.md) | O que fica em cada pasta e em cada módulo |

## Explicação

Contexto e motivos, para quem quer entender antes de mudar.

| Página | Assunto |
|---|---|
| [Arquitetura](explicacao/arquitetura.md) | Monólito modular, camadas, módulos e como eles conversam |
| [Pipeline de processamento](explicacao/pipeline.md) | O caminho de uma mídia, do envio ao resumo, e como falhas são recuperadas |
| [Segurança](explicacao/seguranca.md) | Sessão, tokens, regra de acesso, proteção da execução e da cadeia de suprimentos |
| [Operação e confiabilidade](explicacao/operacao.md) | Implantação contínua, saúde, logs, métricas e cópias de segurança |
| [Decisões de arquitetura (ADRs)](adr/decisions.md) | O registro de cada decisão, com contexto, alternativas e consequências |

## Como esta documentação é mantida

- **Junto com o código.** Fica no repositório, muda no mesmo PR que muda o
  comportamento e passa pela mesma revisão. Por isso não há uma Wiki separada:
  ela ficaria fora da revisão e se afastaria do código sem ninguém notar.
- **Referência gerada.** Depois de mudar rotas, configurações ou eventos, rode
  `python scripts/docs/gerar_referencia.py`. O teste
  `tests/unit/test_docs_reference.py` falha se a referência ficar para trás.
- **Verificada na CI.** O job `docs` confere o Markdown (markdownlint) e todos
  os links internos, inclusive as âncoras (lychee).
- **Regras do código.** As regras que todo PR segue estão em
  [`AGENTS.md`](../AGENTS.md); o relatório do TCC fica no repositório
  `relatorio_tcc`.
