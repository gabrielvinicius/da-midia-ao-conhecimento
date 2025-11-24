# Guidelines para Migrations do Alembic

Este documento descreve as melhores práticas e workflow para lidar com migrations do Alembic no projeto video-summarizer, para evitar problemas como heads múltiplos.

## Problema Comum: Heads Múltiplos

O problema de "multiple heads" ocorre quando duas ou mais branches de desenvolvimento criam migrations separadamente, e ao integrar as branches, o Alembic não sabe qual caminho seguir.

## Solução Implementada

O problema foi resolvido criando uma migration de merge:

```bash
alembic merge -m "merge_heads_resolved"
```

## Workflow Recomendado para Prevenir o Problema

### 1. Antes de Criar uma Nova Migration

Sempre atualize sua branch com o branch principal antes de criar uma migration:

```bash
git checkout main
git pull origin main
git checkout minha-feature
git merge main
# ou git rebase main
```

### 2. Verificando o Status Atual das Migrations

Antes de trabalhar com migrations, verifique o status atual:

```bash
alembic heads      # Verifica se há múltiplos heads
alembic current    # Verifica a revisão atual do banco
alembic history    # Verifica o histórico de migrations
```

### 3. Criando uma Nova Migration

Quando você alterar modelos SQLAlchemy, gere uma migration:

```bash
alembic revision --autogenerate -m "descrição_da_mudança"
```

### 4. Antes de Fazer Merge da Sua Branch

Verifique se não há conflitos de migration:

```bash
# Na sua branch
alembic heads
# Deve mostrar apenas um head
```

Se houver múltiplos heads, resolva com:

```bash
alembic merge -m "merge_heads_from_feature_branch"
```

### 5. Script de Validação

O projeto inclui um script para validar migrations:

```bash
python scripts/validate_migrations.py
```

Este script pode ser adicionado ao seu pipeline de CI para garantir que não haja heads múltiplos.

## Validação Automática

Um hook de pre-commit está disponível em `scripts/pre_commit_hook.sh` que pode ser instalado para validar migrations antes de cada commit.

## Recuperação de Emergência

Se você encontrar múltiplos heads:

1. Execute `alembic heads` para identificar os heads problemáticos
2. Execute `alembic merge -m "mensagem_clara"` para criar uma migration de merge
3. Execute `alembic upgrade head` para aplicar a migration de merge
4. Execute `alembic heads` novamente para confirmar que há apenas um head

## Boas Práticas

- Sempre atualize sua branch com o branch principal antes de trabalhar com migrations
- Revise migrations nos pull requests
- Use mensagens de commit claras para migrations
- Evite criar migrations em branches paralelas sem integrar com o branch principal regularmente