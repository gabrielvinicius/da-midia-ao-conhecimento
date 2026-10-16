# Cópias de segurança

As cópias guardam o banco, as mídias enviadas e, quando o S3 local está
ligado, os dados do Garage, num repositório [restic](https://restic.readthedocs.io/):
incremental (só o que mudou é gravado), com deduplicação e cifrado. Este guia
mostra como configurar, conferir e restaurar. Os motivos das escolhas estão no
ADR-018.

| O que | Como é copiado |
|---|---|
| Banco (PostgreSQL) | `pg_dump -Fc`, primeiro para um arquivo; um dump vazio interrompe a cópia |
| Mídias | A pasta `MEDIA_STORAGE_PATH`, ou o volume `media_data` |
| S3 local (Garage) | O volume do Garage, com a cópia consistente que ele mesmo tira do banco de metadados |

Os modelos de IA não entram: eles são baixados de novo.

## Configurar

No `.env` da produção:

```env
BACKUP_REPOSITORY=C:/backups/restic
BACKUP_PASSWORD=<uma chave longa e aleatória>
```

- **`BACKUP_REPOSITORY`**: uma pasta do host, de preferência num disco
  diferente do das mídias, ou um destino remoto do restic (`s3:...`, `b2:...`,
  `rclone:...`). O repositório é criado na primeira cópia.
- **`BACKUP_PASSWORD`**: cifra o repositório. Para gerar uma:
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- **Retenção** (opcional): `BACKUP_KEEP_DAILY`, `BACKUP_KEEP_WEEKLY` e
  `BACKUP_KEEP_MONTHLY`; o padrão guarda 14 diárias, 8 semanais e 12 mensais.

> [!CAUTION]
> Guarde `BACKUP_PASSWORD` fora da máquina, num gerenciador de senhas. Sem ela,
> nenhuma cópia pode ser lida, nem por você.

## Como as cópias rodam

O workflow **Backup** roda todo dia às 03:23 (horário de Brasília), no runner
de produção, e executa `scripts/ops/backup.sh`. Ao final, aplica a retenção e
confere a integridade do repositório (`restic check`). Aos domingos, roda
também o teste de restauração. Uma execução com falha avisa por e-mail, como
qualquer workflow do GitHub.

Para fazer uma cópia agora: **Actions > Backup > Run workflow**, ou, na pasta de
produção, com o Git Bash:

```bash
sh scripts/ops/backup.sh
```

## Conferir se a cópia restaura

Uma cópia só vale se restaurar. O teste restaura o banco mais recente num
PostgreSQL temporário, isolado da produção, e confere tabelas, migração,
usuários e mídias; lê de volta 5% dos dados do repositório; e, com o Garage,
confere que a cópia do banco de metadados está lá.

```bash
sh scripts/ops/verify-backup.sh
```

Pelo GitHub: **Actions > Backup > Run workflow**, marcando **verify**. A saída
termina assim:

```text
[verify] 10 tabelas, migração d9b3e7a1c4f6, 4 usuários, 22 mídias
[verify] S3 local: 2 cópias do banco de metadados do Garage
[verify] cópia restaurável
```

## Restaurar

> [!WARNING]
> A restauração **substitui** o banco e as mídias atuais. Arquivos que não
> estavam na cópia são apagados. Faça antes uma cópia do estado atual, se ele
> ainda tiver valor.

1. Escolha a cópia. Para ver as disponíveis:

   ```bash
   . scripts/ops/restic-env.sh && restic "$RESTIC_IMAGE" snapshots
   ```

2. Restaure, na pasta de produção, com o banco no ar:

   ```bash
   sh scripts/ops/restore.sh            # a cópia mais recente
   sh scripts/ops/restore.sh <snapshot> # uma cópia específica
   ```

   O script para os workers, restaura o banco (`pg_restore --clean`), as
   mídias e, se houver, os dados do Garage, e religa os workers. No Garage, ele
   segue a documentação do próprio Garage: com o serviço parado, a cópia do
   banco de metadados vira o banco, e um reparo (`garage repair tables`) acerta
   o que mudou depois dela.
3. Confira a plataforma: entre, abra uma mídia e reproduza o vídeo.

## Cópia fora da máquina

Com o repositório numa pasta local, a regra 3-2-1 (três cópias, em duas mídias,
uma fora do local) ainda não é cumprida. `BACKUP_REPOSITORY` já aceita um
destino remoto do restic (`s3:https://<endpoint>/<bucket>`), mas o contêiner do
restic hoje recebe só o repositório e a chave: as credenciais do serviço
(`AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`) ainda precisam ser repassadas
pela função `restic` de `scripts/ops/restic-env.sh`. Essa segunda cópia está
entre os [limites conhecidos](../explicacao/operacao.md#limites-conhecidos).

## Veja também

- [Solucionar problemas](solucionar-problemas.md#cópia-de-segurança-falhou):
  o workflow Backup falhou.
- [Comandos](../referencia/comandos.md#cópias-de-segurança): os scripts e as
  variáveis que eles leem.
