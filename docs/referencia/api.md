<!-- Gerado por scripts/docs/gerar_referencia.py a partir do código. Não edite à mão: rode o script. -->

# Referência da API

API REST do sistema (FastAPI, versão `2.0.0`), com 69 operações. Na instalação com o Compose, ela fica atrás do Nginx do frontend, no prefixo `/api` (por exemplo, `POST /api/auth/token`). A especificação completa, com os esquemas, sai em `/docs` e `/openapi.json` no ambiente de desenvolvimento.

- **público**: sem login.
- **com sessão**: cabeçalho `Authorization: Bearer <token de acesso>` (`POST /auth/token`); o token de renovação vai num cookie `httpOnly`.
- **administrador**: com sessão e papel `ADMIN`.

Dono ou administrador: uma mídia de outra pessoa responde 404, e não 403 (veja [Segurança](../explicacao/seguranca.md)).

## Autenticação e conta

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `POST` | `/auth/forgot-password` | público | Mesma resposta com ou sem conta: não revela quem está cadastrado. |
| `POST` | `/auth/logout` | público | Revoga o token de renovação e apaga o cookie. |
| `GET` | `/auth/me` | com sessão | Usuário da sessão |
| `PUT` | `/auth/me/password` | com sessão | Troca a senha do usuário logado, exigindo a senha atual. |
| `GET` | `/auth/options` | público | Opções da conta (envio de e-mails ligado?) |
| `POST` | `/auth/refresh` | público | Renovar a sessão pelo cookie de renovação |
| `POST` | `/auth/register` | público | Cria a conta. Com o envio de e-mails ligado, ela só entra depois de confirmar o e-mail (email_verification_required). |
| `POST` | `/auth/resend-verification` | público | Mesma resposta com ou sem conta: não revela quem está cadastrado. |
| `POST` | `/auth/reset-password` | público | Definir nova senha pelo link recebido |
| `POST` | `/auth/scoped-token` | com sessão | Token de finalidade restrita para onde o navegador não manda cabeçalho: a URL do vídeo (por mídia) e a abertura do WebSocket de avisos. |
| `POST` | `/auth/token` | público | Entrar (e-mail e senha) |
| `POST` | `/auth/verify-email` | público | Confirmar o e-mail pelo link recebido |

## Mídias

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/media/` | com sessão | Mídias do usuário |
| `POST` | `/media/` | com sessão | Enviar uma mídia |
| `GET` | `/media/import` | com sessão | Importação por link disponível? |
| `POST` | `/media/import` | com sessão | Baixa o arquivo (ou o vídeo do YouTube) e segue como um envio comum; pode levar minutos. |
| `GET` | `/media/stats` | com sessão | Estatísticas das mídias do usuário |
| `POST` | `/media/uploads` | com sessão | Iniciar um envio em partes |
| `DELETE` | `/media/uploads/{upload_id}` | com sessão | Cancelar um envio em partes |
| `GET` | `/media/uploads/{upload_id}` | com sessão | Situação de um envio em partes |
| `PUT` | `/media/uploads/{upload_id}` | com sessão | Enviar uma parte (corpo: os bytes, a partir de offset) |
| `POST` | `/media/uploads/{upload_id}/complete` | com sessão | Concluir um envio em partes |
| `DELETE` | `/media/{media_id}` | com sessão | Excluir uma mídia |
| `GET` | `/media/{media_id}` | com sessão | Uma mídia pelo id |
| `POST` | `/media/{media_id}/reprocess` | com sessão | Apaga os resultados anteriores e processa a mídia de novo; devolve a mídia já em processamento. Mídia de outro usuário: 404. |
| `GET` | `/media/{media_id}/stream` | público | Bytes da mídia para o reprodutor (com Range) |

## Transcrições

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/transcriptions/` | com sessão | Transcrição de uma mídia |
| `GET` | `/transcriptions/media/{media_id}/estimate` | com sessão | Transcrição + análise, pela duração da gravação e pela velocidade medida nos processamentos anteriores; estimated_seconds é nulo sem base para estimar. |
| `GET` | `/transcriptions/{transcription_id}` | com sessão | Transcrição pelo id |
| `PUT` | `/transcriptions/{transcription_id}/segments/{index}` | com sessão | O texto do modelo fica guardado no trecho; a próxima análise usa o corrigido. |
| `PUT` | `/transcriptions/{transcription_id}/speaker-aliases` | com sessão | Nomes dos falantes |

## Análise, estudo e busca

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `POST` | `/text-analysis/analyze` | com sessão | Pede uma nova análise da mídia ao worker; o resultado chega pelos avisos. |
| `GET` | `/text-analysis/media/{media_id}` | com sessão | Análise de uma mídia |
| `GET` | `/text-analysis/notebook` | com sessão | O caderno de resumos de quem pede, das mídias mais novas para as mais antigas. |
| `GET` | `/text-analysis/search` | com sessão | Busca semântica nas mídias do usuário (administradores veem todas). |
| `GET` | `/text-analysis/study-deck` | com sessão | As perguntas de revisão (com a resposta e o momento da gravação) de todas as análises de quem pede, das mais novas para as mais antigas. |
| `GET` | `/text-analysis/topics-overview` | com sessão | Temas de todas as mídias de quem pede, juntos pelo título; os que se repetem em mais mídias primeiro. |
| `GET` | `/text-analysis/{analysis_id}` | com sessão | Análise pelo id |
| `POST` | `/text-analysis/{analysis_id}/feedback` | com sessão | Registra a avaliação humana de uma análise (no corpo, não na URL). |
| `POST` | `/text-analysis/{analysis_id}/review-answer` | com sessão | Acertou: a pergunta volta mais tarde (1, 3, 7, 14 dias). Errou: volta hoje. |
| `PUT` | `/text-analysis/{analysis_id}/study` | com sessão | Corrige capítulos e perguntas de revisão, preservando a versão da IA. |
| `PUT` | `/text-analysis/{analysis_id}/summary` | com sessão | Corrige o resumo gerado pela IA, preservando o original. |
| `GET` | `/text-analysis/{analysis_id}/topics` | com sessão | Temas de uma análise |
| `PUT` | `/text-analysis/{analysis_id}/topics/{topic_id}` | com sessão | Corrige o título de um tema, preservando o dado pela IA. |

## Avisos

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/notifications/` | com sessão | Avisos mais recentes do usuário |
| `POST` | `/notifications/read-all` | com sessão | Marcar todos os avisos como lidos |
| `POST` | `/notifications/{notification_id}/read` | com sessão | Marcar um aviso como lido |

## Opções do processamento

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/providers` | com sessão | Lista providers selecionáveis no pipeline |

## Monitoramento

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/monitoring/ping` | público | Resposta mínima (a API está no ar?) |
| `GET` | `/monitoring/system-status` | com sessão | Nível de carga da máquina |

## Administração

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/admin/media` | administrador | Mídias de todos os usuários |
| `POST` | `/admin/media/bulk-reprocess` | administrador | Reprocessa até ``limit`` mídias com falha, das mais antigas para as mais novas; ``more_pending`` indica que há outras para um próximo pedido. |
| `DELETE` | `/admin/media/{media_id}` | administrador | Excluir uma mídia |
| `POST` | `/admin/media/{media_id}/reprocess` | administrador | Reprocessar uma mídia que falhou |
| `GET` | `/admin/quality` | administrador | Quanto da saída da IA os usuários corrigiram (resumo, temas, capítulos, perguntas e trechos da transcrição) e como a avaliaram. |
| `GET` | `/admin/queue` | administrador | Mídias em andamento na ordem de chegada, há quanto tempo cada uma está na etapa atual (e se parece parada) e as tarefas esperando no Celery. |
| `GET` | `/admin/server` | administrador | CPU, memória e GPU (placa inteira, lida pelo worker pesado), e se o banco, o Redis, o Ollama e os workers respondem. |
| `GET` | `/admin/stats` | administrador | Estatísticas gerais |
| `GET` | `/admin/stats/health` | administrador | Alertas do sistema |
| `GET` | `/admin/stats/media-processing` | administrador | Mídias por estado |
| `GET` | `/admin/stats/processing-times` | administrador | Execuções, falhas, média, mediana, máximo e fator de tempo real por tarefa. |
| `GET` | `/admin/users` | administrador | Usuários |
| `DELETE` | `/admin/users/{user_id}` | administrador | Excluir um usuário |
| `PUT` | `/admin/users/{user_id}` | administrador | Alterar o perfil de um usuário |
| `POST` | `/admin/users/{user_id}/activate` | administrador | Reativar uma conta |
| `GET` | `/admin/users/{user_id}/activity` | administrador | Atividade de um usuário |
| `POST` | `/admin/users/{user_id}/deactivate` | administrador | Desativar uma conta |

## Saúde

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/health` | público | Saúde da API, do banco e do Redis (503 se algum falhar) |

## Outros

| Método | Caminho | Acesso | O que faz |
|---|---|---|---|
| `GET` | `/` | público | Root endpoint with API information. |
