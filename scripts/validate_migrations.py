#!/usr/bin/env python3
"""Script de validação de migrations do Alembic
Este script verifica se há heads múltiplos nas migrations do Alembic
e garante que as migrations estejam em um estado consistente.
"""

import subprocess
import sys
from typing import List, Tuple


def run_alembic_command(command: str) -> Tuple[str, str, int]:
    """Executa um comando Alembic e retorna saída, erro e código de retorno
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd="/app" if is_running_in_container() else "."
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


def is_running_in_container() -> bool:
    """Verifica se o script está rodando dentro de um container
    """
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read() or "containerd" in f.read()
    except FileNotFoundError:
        return False


def check_multiple_heads() -> List[str]:
    """Verifica se há múltiplos heads no Alembic
    Retorna uma lista com os heads ou uma lista vazia se não houver múltiplos heads
    """
    stdout, stderr, returncode = run_alembic_command("alembic heads")

    if returncode != 0:
        print(f"Erro ao executar 'alembic heads': {stderr}")
        return []

    heads = [line.strip() for line in stdout.split('\n') if line.strip() and '(head)' in line]
    head_revisions = [head.split()[0] for head in heads]

    return head_revisions


def check_current_revision() -> str:
    """Verifica a revisão atual do banco de dados
    """
    stdout, stderr, returncode = run_alembic_command("alembic current")

    if returncode != 0:
        print(f"Erro ao executar 'alembic current': {stderr}")
        return ""

    # Extrai a revisão atual do output
    for line in stdout.split('\n'):
        if '(head)' in line or '(base)' in line:
            return line.split()[0]

    return ""


def generate_revision_if_needed() -> bool:
    """Gera uma migration automática se houver diferenças não detectadas
    """
    stdout, stderr, returncode = run_alembic_command("alembic revision --autogenerate -m 'auto'")

    if returncode != 0:
        if "No changes detected" in stderr or "No changes detected" in stdout:
            print("Nenhuma alteração detectada, nenhuma migration necessária")
            return True
        else:
            print(f"Erro ao gerar migration automática: {stderr}")
            return False

    print("Migration automática gerada com sucesso")
    return True


def check_migration_status() -> bool:
    """Verifica o status geral das migrations
    """
    print("Verificando status das migrations...")

    # Verifica heads múltiplos
    heads = check_multiple_heads()
    if len(heads) > 1:
        print(f"ERRO: Encontrados múltiplos heads: {heads}")
        return False
    elif len(heads) == 1:
        print(f"OK: Apenas um head encontrado: {heads[0]}")
    else:
        print("Nenhum head encontrado")
        return False

    # Verifica revisão atual
    current = check_current_revision()
    if current:
        print(f"OK: Revisão atual do banco: {current}")
    else:
        print("ERRO: Não foi possível determinar a revisão atual")
        return False

    # Verifica se há diferenças necessitando de migration
    generate_revision_if_needed()

    print("Todas as verificações passaram!")
    return True


def main():
    """Função principal do script de validação
    """
    print("Iniciando validação de migrations do Alembic...")

    if not check_migration_status():
        print("\nFalha na validação de migrations!")
        sys.exit(1)

    print("\nValidação de migrations concluída com sucesso!")
    sys.exit(0)


if __name__ == "__main__":
    main()
