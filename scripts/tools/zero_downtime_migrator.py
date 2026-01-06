"""Utilitário para Automação de Migrações Expand & Contract (Nível 6.0)."""
import argparse
import os
import subprocess
from datetime import datetime

def run_command(cmd):
    print(f"Executando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Erro: {result.stderr}")
    else:
        print(result.stdout)
    return result.returncode == 0

def create_expand(args):
    """Gera migração para adicionar uma coluna."""
    msg = f"expand_add_{args.column}_to_{args.table}"
    print(f"--- FASE 1: EXPAND ({msg}) ---")
    
    # Comando Alembic para gerar o scaffold
    cmd = ["alembic", "revision", "-m", msg]
    run_command(cmd)
    
    print("\n[DICA] Edite o arquivo gerado em alembic/versions/ para incluir:")
    print(f"op.add_column('{args.table}', sa.Column('{args.column}', sa.{args.type}(), nullable=True))")

def create_contract(args):
    """Gera migração para remover uma coluna."""
    msg = f"contract_remove_{args.column}_from_{args.table}"
    print(f"--- FASE 3: CONTRACT ({msg}) ---")
    
    cmd = ["alembic", "revision", "-m", msg]
    run_command(cmd)
    
    print("\n[DICA] Edite o arquivo gerado em alembic/versions/ para incluir:")
    print(f"op.drop_column('{args.table}', '{args.column}')")

def main():
    parser = argparse.ArgumentParser(description="Zero-Downtime Migration Helper")
    subparsers = parser.add_subparsers(dest="command")

    # Expand command
    expand_parser = subparsers.add_parser("expand", help="Add a new column (nullable)")
    expand_parser.add_argument("--table", required=True, help="Table name")
    expand_parser.add_argument("--column", required=True, help="New column name")
    expand_parser.add_argument("--type", default="String", help="SQLAlchemy type (String, Integer, etc.)")

    # Contract command
    contract_parser = subparsers.add_parser("contract", help="Remove an old column")
    contract_parser.add_argument("--table", required=True, help="Table name")
    contract_parser.add_argument("--column", required=True, help="Old column name to remove")

    args = parser.parse_args()

    if args.command == "expand":
        create_expand(args)
    elif args.command == "contract":
        create_contract(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
