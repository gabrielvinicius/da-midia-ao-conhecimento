# Política de Evolução de Esquema Sem Parada (Nível 6.0)

Este documento descreve o padrão **Expand and Contract** utilizado para realizar alterações no banco de dados sem indisponibilidade (Zero-Downtime).

## O Ciclo de Vida de uma Mudança de Esquema

Nunca realize uma alteração destrutiva (renomear ou remover coluna) em um único deploy. Siga estas três etapas:

### 1. Fase de Expansão (Deploy N)
*   **Banco de Dados:** Adicione a nova coluna como opcional (`nullable=True`).
*   **Código:** Atualize a aplicação para escrever em **ambas** as colunas (Dual Write), mas continuar lendo da coluna antiga.
*   **Ferramenta:** `python scripts/tools/zero_downtime_migrator.py expand --table users --column new_field --type String`

### 2. Fase de Migração (Intermediária)
*   **Ação:** Execute uma tarefa de fundo (Celery) para copiar os dados da coluna antiga para a nova em todos os registros existentes.
*   **Verificação:** Garanta que todos os registros possuem o novo campo preenchido.

### 3. Fase de Contração (Deploy N+1)
*   **Código:** Atualize a aplicação para ler e escrever **apenas** na nova coluna.
*   **Banco de Dados:** Remova a coluna antiga.
*   **Ferramenta:** `python scripts/tools/zero_downtime_migrator.py contract --table users --column old_field`

## Regras de Ouro
1.  **Retrocompatibilidade:** O código do deploy N+1 deve ser capaz de rodar enquanto o banco do deploy N ainda existe (e vice-versa em caso de rollback).
2.  **JSONB:** Para o módulo `text_analysis`, prefira a evolução via **Upcasting** (versão no payload JSON) em vez de migrações estruturais de tabela quando possível.
3.  **Locks:** Evite `ALTER TABLE` que causem locks longos em tabelas com milhões de registros. Adicione índices de forma `CONCURRENTLY`.
