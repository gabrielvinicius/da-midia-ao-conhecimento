<!-- Gerado por scripts/docs/gerar_referencia.py a partir do código. Não edite à mão: rode o script. -->

# Referência da configuração

Variáveis de ambiente lidas pelo sistema, com o valor padrão do código. Na instalação com o Compose, elas vêm do `.env` (copie o `.env.example`); o `docker-compose.yml` sobrescreve os endereços dos serviços (banco, Redis, Ollama, Jaeger) e `APP_ENV=production`. Um teste confere que toda variável do `.env.example` é lida por alguma configuração.

A coluna **.env.example** marca as que aparecem lá, com explicação; as demais têm um padrão adequado e raramente mudam. Para trocar modelos e etapas, veja [Trocar modelos e etapas da análise](../guias/modelos-e-etapas.md).

## Gerais (API, workers, modelos)

`Settings` em `src/shared/infrastructure/config/settings.py`.

| Variável | Padrão | .env.example | Descrição |
|---|---|---|---|
| `APP_ENV` | `development` | sim | "production" no docker-compose; "development" libera o transcritor de mentira, usado só sem os modelos instalados. |
| `LIGHTWEIGHT_BOOTSTRAP` | `false` |  |  |
| `DATABASE_URL` | `sqlite+aiosqlite:///./app.db` | sim | Sem o compose, aponte para os serviços na própria máquina: |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174` | sim | Origens aceitas pelo CORS, separadas por vírgula (CORS_ORIGINS). Em produção o frontend chega pelo proxy do Nginx, na mesma origem. |
| `REDIS_URL` | `redis://localhost:6379/0` | sim | Sem o compose, aponte para os serviços na própria máquina: |
| `OLLAMA_HOST` | `http://localhost:11434` | sim | Ollama (LLM local): endereço do servidor e modelos padrão |
| `LLM_MODEL` | `qwen3.5:9b` | sim | Modelo de linguagem (Ollama) do resumo e dos títulos dos temas, e o reserva. |
| `LLM_FALLBACK_MODEL` | `gemma4:e4b` | sim | Modelo de linguagem (Ollama) do resumo e dos títulos dos temas, e o reserva. |
| `LLM_CONTEXT_TOKENS` | `16384` | sim | 16k tokens: cabe nos prompts do pipeline (síntese em blocos) sem que o cache de contexto do Ollama ocupe GBs a mais da GPU de 12 GB. |
| `LLM_TIMEOUT_SECONDS` | `900` |  |  |
| `ANALYSIS_TIME_LIMIT_MINUTES` | `150` | sim | Tempo máximo de uma análise no worker. Fica abaixo do prazo em que a mídia "em análise" é dada como falha (MEDIA_ANALYSIS_GIVE_UP_MINUTES, 180), para que a falha venha da própria análise, com o motivo. |
| `ANALYSIS_FACTORS` | `sentiment,topics,grounding,chapters,questions` | sim | Fatores opcionais da análise, separados por vírgula: sentiment, topics (temas e seus títulos), grounding (verificação de fidelidade), chapters (capítulos com horário) e questions (perguntas de revisão). |
| `VISUAL_PROVIDER` | `ollama` | sim | Descrição de quadros de vídeo: "ollama" (padrão; o mesmo Qwen3.5 do resumo, que aceita imagens), "moondream" ou "none" (desligada). Comparados nos mesmos quadros de uma aula: o Qwen3.5 descreve em português e transcreve os textos da tela (nomes, títulos de livros), o Moondream só dizia "um homem fala ao microfone"; e não carrega um segundo modelo de ~4 GB na GPU. Custa ~4 s por quadro (Moondream, ~2 s). |
| `VISUAL_OLLAMA_MODEL` | `qwen3.5:9b` | sim | Descrição dos quadros do vídeo: ollama (o mesmo modelo do resumo, que aceita imagens: descreve em português e lê os textos da tela), moondream (mais leve, descrições curtas em inglês) ou none (desligada). |
| `AI_DEVICE` | `auto` |  | AI / Machine Learning Hardware Options: "auto", "cuda", "cpu", "rocm" |
| `AI_COMPUTE_TYPE` | `default` | sim | Options: "float16", "float32", "int8", "int8_float16" |
| `WHISPER_MODEL` | `large-v3-turbo` | sim | Modelo de transcrição (Faster-Whisper ou openai-whisper). |
| `WHISPER_HOTWORDS` | (vazio) | sim | Termos do domínio (separados por vírgula) que orientam a transcrição. O Whisper acerta a fala comum e erra justo o jargão: numa aula de engenharia de software, "overengineering" saiu "o Wolverine de Neil" e "KISS, DRY e YAGNI" saiu "Keys, Draw e Agni". Vazio: sem glossário. |
| `SEARCH_RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | sim | Reranqueador da busca semântica: reordena os 20 trechos mais parecidos lendo pergunta e trecho juntos. Numa aula de 30 min, o trecho certo ficou em 1º em 7 de 8 perguntas (4 de 8 só com os vetores). Roda na CPU da API (~2 GB de memória). Vazio: só os vetores. |

## Mídias e envios

`MediaSettings` em `src/media_management/config/settings.py`.

| Variável | Padrão | .env.example | Descrição |
|---|---|---|---|
| `MEDIA_STORAGE_PROVIDERS_ALLOWED` | `local,s3` |  |  |
| `MEDIA_TRANSCRIPTION_PROVIDERS_ALLOWED` | `default,fastwhisper,openai-whisper` |  | Nomes do catálogo de transcrição (media_processing); um nome fora da lista só gera aviso, e o worker usa o padrão. |
| `MEDIA_MEDIA_MIN_FILE_SIZE_BYTES` | `1` |  |  |
| `MEDIA_MEDIA_MAX_FILE_SIZE_BYTES` | `524288000` |  |  |
| `MEDIA_MEDIA_UPLOAD_PART_MAX_BYTES` | `67108864` |  | Envio em partes (a Cloudflare recusa requisições acima de 100 MB): maior parte aceita, pasta dos envios em andamento (vazia: a temporária do sistema) e horas até um envio abandonado ser apagado. |
| `MEDIA_MEDIA_UPLOAD_STAGING_DIR` | (vazio) |  |  |
| `MEDIA_MEDIA_UPLOAD_STAGING_HOURS` | `24` |  |  |
| `MEDIA_MEDIA_ALLOWED_AUDIO_EXTENSIONS` | `mp3,wav,flac,aac,ogg,m4a` |  |  |
| `MEDIA_MEDIA_ALLOWED_VIDEO_EXTENSIONS` | `mp4,avi,mov,mkv,webm,flv` |  |  |
| `MEDIA_MEDIA_ALLOWED_TEXT_EXTENSIONS` | `txt,pdf,docx,png,jpg,jpeg,tiff,bmp` |  |  |
| `MEDIA_MEDIA_URL_IMPORT_ENABLED` | `true` |  | Importação de vídeos por link do YouTube (MEDIA_URL_IMPORT_ENABLED). |
| `MEDIA_MEDIA_URL_IMPORT_MAX_MINUTES` | `240` |  |  |
| `MEDIA_UNSTARTED_CHECK_INTERVAL_SECONDS` | `300` | sim | Mídia enviada sem registro de processamento (UnstartedMediaRecovery): anunciada de novo após a folga e marcada como falha após o limite. |
| `MEDIA_UNSTARTED_GRACE_MINUTES` | `10` | sim | Mídia enviada que não ganhou registro de processamento (a API caiu no meio do envio, por exemplo): anunciada de novo após a folga e marcada como falha após o limite. |
| `MEDIA_UNSTARTED_GIVE_UP_MINUTES` | `60` | sim | Mídia enviada que não ganhou registro de processamento (a API caiu no meio do envio, por exemplo): anunciada de novo após a folga e marcada como falha após o limite. |
| `MEDIA_ANALYSIS_GIVE_UP_MINUTES` | `180` | sim | Mídia "em análise" há mais que isto: o worker da análise morreu sem anunciar a falha (UnfinishedAnalysisRecovery). A análise de uma aula de duas horas leva minutos; o limite só pega o que parou de vez. |

## Processamento

`MediaProcessingSettings` em `src/media_processing/config/settings.py`.

| Variável | Padrão | .env.example | Descrição |
|---|---|---|---|
| `PROCESSING_STALL_CHECK_INTERVAL_SECONDS` | `300` | sim | Mídia parada (ver ProcessingDeadlinePolicy). Variáveis PROCESSING_STALL_*. |
| `PROCESSING_STALL_SAFETY_FACTOR` | `3.0` | sim | A cada intervalo, o worker leve marca como falha (o usuário é avisado e pode tentar de novo) as transcrições que passaram do prazo: duração da gravação × tempo por segundo de gravação medido nas anteriores × fator de folga, entre o mínimo e o máximo. Sem histórico, usa o fator padrão (1 = tempo real). |
| `PROCESSING_STALL_MINIMUM_MINUTES` | `20` | sim | A cada intervalo, o worker leve marca como falha (o usuário é avisado e pode tentar de novo) as transcrições que passaram do prazo: duração da gravação × tempo por segundo de gravação medido nas anteriores × fator de folga, entre o mínimo e o máximo. Sem histórico, usa o fator padrão (1 = tempo real). |
| `PROCESSING_STALL_MAXIMUM_HOURS` | `6` | sim | A cada intervalo, o worker leve marca como falha (o usuário é avisado e pode tentar de novo) as transcrições que passaram do prazo: duração da gravação × tempo por segundo de gravação medido nas anteriores × fator de folga, entre o mínimo e o máximo. Sem histórico, usa o fator padrão (1 = tempo real). |
| `PROCESSING_STALL_UNKNOWN_DURATION_MINUTES` | `60` | sim | Documentos, imagens e mídias cuja duração não pôde ser lida: |
| `PROCESSING_STALL_QUEUE_HOURS` | `24` | sim | Tarefa que nunca começou (fila perdida): |
| `PROCESSING_STALL_FALLBACK_REALTIME_FACTOR` | `1.0` | sim | Tarefa que nunca começou (fila perdida): |

## Armazenamento

`StorageSettings` em `src/storage/config/settings.py`.

| Variável | Padrão | .env.example | Descrição |
|---|---|---|---|
| `STORAGE_PROVIDERS_ALLOWED` | `local,s3` |  |  |
| `STORAGE_S3_ENDPOINT_URL` | (vazio) | sim | Serviço compatível com S3. Sem bucket, a opção "s3" não é oferecida. O endpoint fica vazio na AWS; no perfil "s3" do Compose, é o Garage local. |
| `STORAGE_S3_BUCKET` | (vazio) | sim | Com um bucket definido, a opção "S3" aparece no envio, ao lado do armazenamento local. Sem bucket, só o local. S3 na própria máquina (Garage, perfil "s3"): inclua "s3" em COMPOSE_PROFILES e defina o bucket, as chaves e o segredo do Garage; ele cria a chave e o bucket ao subir. Formatos que o Garage exige: STORAGE_S3_ACCESS_KEY: "GK" e 24 caracteres hexadecimais STORAGE_S3_SECRET_KEY e GARAGE_RPC_SECRET: 64 caracteres hexadecimais (por exemplo: openssl rand -hex 32; para a chave, "GK" + openssl rand -hex 12) Em outro serviço S3 (AWS, Cloudflare R2...), defina também o endpoint (vazio na AWS) e deixe o perfil "s3" desligado. |
| `STORAGE_S3_ACCESS_KEY` | (vazio) | sim | Com um bucket definido, a opção "S3" aparece no envio, ao lado do armazenamento local. Sem bucket, só o local. S3 na própria máquina (Garage, perfil "s3"): inclua "s3" em COMPOSE_PROFILES e defina o bucket, as chaves e o segredo do Garage; ele cria a chave e o bucket ao subir. Formatos que o Garage exige: STORAGE_S3_ACCESS_KEY: "GK" e 24 caracteres hexadecimais STORAGE_S3_SECRET_KEY e GARAGE_RPC_SECRET: 64 caracteres hexadecimais (por exemplo: openssl rand -hex 32; para a chave, "GK" + openssl rand -hex 12) Em outro serviço S3 (AWS, Cloudflare R2...), defina também o endpoint (vazio na AWS) e deixe o perfil "s3" desligado. |
| `STORAGE_S3_SECRET_KEY` | (vazio) | sim | Com um bucket definido, a opção "S3" aparece no envio, ao lado do armazenamento local. Sem bucket, só o local. S3 na própria máquina (Garage, perfil "s3"): inclua "s3" em COMPOSE_PROFILES e defina o bucket, as chaves e o segredo do Garage; ele cria a chave e o bucket ao subir. Formatos que o Garage exige: STORAGE_S3_ACCESS_KEY: "GK" e 24 caracteres hexadecimais STORAGE_S3_SECRET_KEY e GARAGE_RPC_SECRET: 64 caracteres hexadecimais (por exemplo: openssl rand -hex 32; para a chave, "GK" + openssl rand -hex 12) Em outro serviço S3 (AWS, Cloudflare R2...), defina também o endpoint (vazio na AWS) e deixe o perfil "s3" desligado. |
| `STORAGE_S3_REGION` | `us-east-1` |  |  |

## Usuários, sessão e e-mail

`UserSettings` em `src/user_management/config/settings.py`.

| Variável | Padrão | .env.example | Descrição |
|---|---|---|---|
| `USER_SECRET_KEY` / `SECRET_KEY` | `insecure-secret-key-for-dev` | sim | Chave que assina os tokens JWT. Aceita USER_SECRET_KEY ou SECRET_KEY (o nome usado no .env.example); antes só USER_SECRET_KEY era lida, e a chave pública de desenvolvimento assinava os tokens sem aviso. |
| `USER_ALGORITHM` | `HS256` |  |  |
| `USER_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | sim | Validade do token de acesso (minutos) e da sessão (renovação, minutos). |
| `USER_REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` | sim | Validade do token de acesso (minutos) e da sessão (renovação, minutos). |
| `USER_STREAM_TOKEN_EXPIRE_MINUTES` | `360` |  | Tokens de finalidade restrita (application/tokens.py): o do reprodutor cobre uma aula longa; o do WebSocket só precisa durar até conectar. |
| `USER_SOCKET_TOKEN_EXPIRE_SECONDS` | `120` |  |  |
| `USER_AUTH_PASSWORD_MIN_LENGTH` | `8` |  |  |
| `USER_COOKIE_SECURE` | `false` | sim | Com HTTPS (proxy reverso com certificado), ligue para o cookie da sessão só trafegar cifrado. Sem HTTPS, deixe desligado: o navegador o descartaria. |
| `USER_COOKIE_SAMESITE` | `lax` |  |  |
| `USER_LIGHTWEIGHT_MODE` | `false` |  |  |
| `USER_LOGIN_MAX_ATTEMPTS_PER_EMAIL` | `5` | sim | Proteção contra força bruta no login (janela e bloqueio em segundos) |
| `USER_LOGIN_MAX_ATTEMPTS_PER_IP` | `20` | sim | Após N falhas (por e-mail ou por IP) no período, o login fica bloqueado. |
| `USER_LOGIN_BLOCK_SECONDS` | `900` | sim | Após N falhas (por e-mail ou por IP) no período, o login fica bloqueado. |
| `PUBLIC_URL` / `USER_PUBLIC_URL` | `http://localhost:3000` | sim | Endereço público da aplicação, usado nos links enviados por e-mail. |
| `SMTP_HOST` | (vazio) | sim | Envio de e-mails (confirmação do cadastro e nova senha). Opcional: sem SMTP_HOST, o cadastro entra direto e a recuperação de senha não aparece. Funciona com qualquer provedor SMTP (Resend, Brevo, Gmail, Amazon SES...). |
| `SMTP_PORT` | `587` | sim | Envio de e-mails: confirmação do cadastro e recuperação de senha. Sem SMTP_HOST, o cadastro entra direto e "Esqueci minha senha" não aparece. Qualquer provedor SMTP serve. Ex. (Resend): SMTP_HOST=smtp.resend.com, |
| `SMTP_USERNAME` | (vazio) | sim | Envio de e-mails: confirmação do cadastro e recuperação de senha. Sem SMTP_HOST, o cadastro entra direto e "Esqueci minha senha" não aparece. Qualquer provedor SMTP serve. Ex. (Resend): SMTP_HOST=smtp.resend.com, |
| `SMTP_PASSWORD` | (vazio) | sim | Envio de e-mails: confirmação do cadastro e recuperação de senha. Sem SMTP_HOST, o cadastro entra direto e "Esqueci minha senha" não aparece. Qualquer provedor SMTP serve. Ex. (Resend): SMTP_HOST=smtp.resend.com, |
| `SMTP_FROM` | (vazio) | sim | Remetente, ex.: "Da Mídia ao Conhecimento <no-reply@seudominio>". |
| `SMTP_SECURITY` | `starttls` | sim | starttls (porta 587), ssl (465) ou none (servidor local de testes). |
| `USER_EMAIL_VERIFICATION_HOURS` | `24` |  |  |
| `USER_PASSWORD_RESET_MINUTES` | `60` |  |  |

## Lidas fora das classes de configuração

Usadas pelo Compose, pelos scripts de operação ou por bibliotecas (lista em `READ_ELSEWHERE`, `tests/unit/test_deployment_config.py`):

- `BACKUP_KEEP_DAILY`
- `BACKUP_KEEP_MONTHLY`
- `BACKUP_KEEP_WEEKLY`
- `BACKUP_PASSWORD`
- `BACKUP_REPOSITORY`
- `CELERY_BROKER_URL`
- `CLOUDFLARE_TUNNEL_TOKEN`
- `COMPOSE_PROFILES`
- `DB_NAME`
- `DB_PASSWORD`
- `DB_SCHEME`
- `DB_USER`
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_FORCE_PASSWORD`
- `DEFAULT_ADMIN_PASSWORD`
- `GARAGE_RPC_SECRET`
- `HF_TOKEN`
- `LOG_FORMAT`
- `LOG_LEVEL`
- `MEDIA_STORAGE_PATH`
- `METRICS_PORT`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
