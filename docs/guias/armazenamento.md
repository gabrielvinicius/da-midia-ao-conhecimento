# Armazenamento

As mídias enviadas ficam no **armazenamento local** por padrão. Este guia
mostra como colocá-las em outro disco, como ligar o **S3 local** (Garage) e
como usar um **serviço S3 externo**. A troca acontece por configuração: o
código fala com o armazenamento por uma porta (`StoragePort`), e cada destino
é um adaptador (veja [Arquitetura](../explicacao/arquitetura.md)).

Quando há mais de um destino, quem envia escolhe no formulário de envio; cada
mídia guarda o destino em que foi gravada.

## Mídias em outro disco

Por padrão, as mídias ficam no volume `media_data` do Docker. Para usar uma
pasta do host, como um disco só para elas:

1. Crie a pasta e dê a posse ao usuário do contêiner (uid 999):

   ```powershell
   docker run --rm -v D:/da-midia-ao-conhecimento/midias:/s alpine:3.22 chown 999:999 /s
   ```

2. No `.env`:

   ```env
   MEDIA_STORAGE_PATH=D:/da-midia-ao-conhecimento/midias
   ```

3. Se já houver mídias no volume, copie-as para a pasta antes de reiniciar,
   preservando o dono, e reinicie com `docker compose up -d`.

> [!NOTE]
> No Docker Desktop, um disco instalado depois de o Docker iniciar só fica
> visível para os contêineres após `wsl --shutdown` e um novo início do
> Docker Desktop.

As cópias de segurança seguem a mesma escolha: copiam a pasta, se definida, ou
o volume.

## S3 local (Garage)

O perfil `s3` do Compose sobe o [Garage](https://garagehq.deuxfleurs.fr/), um
armazenamento compatível com S3 feito para auto-hospedagem pequena. Ele roda
na própria máquina, só na rede interna dos contêineres, e serve para mostrar a
troca de armazenamento sem depender de um serviço externo. Por que o Garage, e
não o MinIO: ADR-019.

1. Gere os valores. A chave de acesso precisa de `GK` mais 24 caracteres
   hexadecimais; o segredo da chave e o segredo interno do Garage, de 64:

   ```powershell
   $hex = { param($n) $b = New-Object byte[] $n; [Security.Cryptography.RandomNumberGenerator]::Fill($b); -join ($b | ForEach-Object { $_.ToString('x2') }) }
   "STORAGE_S3_ACCESS_KEY=GK$(& $hex 12)"
   "STORAGE_S3_SECRET_KEY=$(& $hex 32)"
   "GARAGE_RPC_SECRET=$(& $hex 32)"
   ```

2. No `.env`, com os valores gerados:

   ```env
   COMPOSE_PROFILES=internet,s3
   STORAGE_S3_BUCKET=midias
   STORAGE_S3_ACCESS_KEY=GK...
   STORAGE_S3_SECRET_KEY=...
   GARAGE_RPC_SECRET=...
   ```

   Sem o túnel, use só `COMPOSE_PROFILES=s3`. Deixe `STORAGE_S3_ENDPOINT_URL`
   vazio: o padrão já aponta para o Garage (`http://garage:3900`).
3. Aplique com `docker compose up -d`. Ao subir pela primeira vez, o Garage
   cria a chave e o bucket do `.env`.
4. Confira: o serviço `garage` aparece como `healthy` em `docker compose ps`, e
   o formulário de envio passa a oferecer **S3** ao lado de **Local (Filesystem)**.

> [!IMPORTANT]
> O Garage aqui é um nó só, sem réplica: os dados ficam no mesmo disco. Ele
> demonstra a troca de armazenamento, mas não dá mais segurança que o
> armazenamento local. A proteção dos dados continua vindo das
> [cópias de segurança](copias-de-seguranca.md), que incluem o volume dele.

## Serviço S3 externo

Para AWS S3, Cloudflare R2 ou outro serviço compatível, deixe o perfil `s3`
desligado e aponte o sistema para o serviço:

```env
STORAGE_S3_BUCKET=<bucket>
STORAGE_S3_ENDPOINT_URL=<endpoint do serviço; vazio na AWS>
STORAGE_S3_ACCESS_KEY=<chave>
STORAGE_S3_SECRET_KEY=<segredo>
STORAGE_S3_REGION=<região do bucket>
```

O bucket é criado na primeira gravação, se não existir. Lembre que um serviço
externo leva as gravações para fora da máquina; avalie se isso é aceitável
para os dados da instituição.

## Veja também

- [Referência da configuração](../referencia/configuracao.md#armazenamento):
  todas as variáveis de armazenamento.
- [Solucionar problemas](solucionar-problemas.md#garage-não-sobe): o Garage
  não sobe.
