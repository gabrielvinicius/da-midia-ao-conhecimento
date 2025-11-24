#!/bin/sh
"""
Script de pre-commit hook para validação de migrations do Alembic
Este script é executado antes de cada commit para garantir que as migrations
estejam em um estado consistente e não haja heads múltiplos.
"""

# Verifica se arquivos de migrations foram modificados
MIGRATION_FILES=$(git diff --cached --name-only | grep -E "alembic/versions/.*\.py$" || true)

if [ -n "$MIGRATION_FILES" ]; then
    echo "Arquivos de migration modificados detectados:"
    echo "$MIGRATION_FILES"
    
    # Verifica se o ambiente tem o alembic disponível
    if command -v alembic >/dev/null 2>&1; then
        echo "Verificando se há múltiplos heads nas migrations..."
        
        # Verificar múltiplos heads
        HEADS_OUTPUT=$(alembic heads 2>&1)
        HEADS_RETURN_CODE=$?
        
        if [ $HEADS_RETURN_CODE -ne 0 ]; then
            echo "ERRO: Falha ao executar 'alembic heads'"
            echo "$HEADS_OUTPUT"
            exit 1
        fi
        
        # Conta quantos heads existem
        HEAD_COUNT=$(echo "$HEADS_OUTPUT" | grep -c "(head)")
        
        if [ $HEAD_COUNT -gt 1 ]; then
            echo "ERRO: Foram detectados múltiplos heads nas migrations:"
            echo "$HEADS_OUTPUT"
            echo ""
            echo "Por favor resolva os heads múltiplos antes de fazer o commit."
            echo "Você pode usar: alembic merge -m 'merge_heads'"
            exit 1
        elif [ $HEAD_COUNT -eq 1 ]; then
            echo "OK: Apenas um head encontrado nas migrations."
        else
            echo "Nenhum head encontrado. Isso pode ser um problema."
            exit 1
        fi
        
        # Verifica se há migrations pendentes
        echo "Verificando se há diferenças não migradas..."
        REVISION_OUTPUT=$(alembic revision --autogenerate --sql 2>&1)
        REVISION_RETURN_CODE=$?
        
        # Verifica se há alterações detectadas (mas não as aplica)
        if echo "$REVISION_OUTPUT" | grep -q "No changes detected"; then
            echo "OK: Nenhuma diferença detectada entre o modelo e o banco."
        else
            echo "AVISO: Foram detectadas diferenças que requerem uma migration."
            echo "Considere gerar uma nova migration com: alembic revision --autogenerate -m 'descricao'"
            # Não sai com erro aqui, pois pode ser uma alteração intencional que ainda não foi migrada
        fi
        
        echo "Validação de migrations concluída com sucesso!"
    else
        echo "AVISO: Alembic não encontrado. Pulando validação de migrations."
    fi
else
    echo "Nenhum arquivo de migration modificado. Pulando validação."
fi

exit 0