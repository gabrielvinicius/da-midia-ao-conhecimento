
import os
import sys
import subprocess
from pathlib import Path

def run():
    print("[migration] Cleaning up old migrations...")
    versions_dir = Path("alembic/versions")
    for f in versions_dir.glob("*.py"):
        f.unlink()
        print(f"  - Deleted {f.name}")

    print("[migration] Generating fresh initial migration for Postgres...")
    # Forçamos a URL síncrona do Postgres para o Alembic
    db_url = os.getenv("DATABASE_URL", "")
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "+psycopg2")
    
    os.environ["SQLALCHEMY_URL"] = db_url

    print("[migration] Cleaning up alembic_version table in DB if exists...")
    try:
        # Tenta deletar a tabela de versão para garantir um novo começo
        import sqlalchemy as sa
        sync_engine = sa.create_engine(db_url.replace("+psycopg2", ""))
        with sync_engine.connect() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
        print("  - DB version history cleared.")
    except Exception as e:
        print(f"  - (Optional) Could not drop alembic_version: {e}")
    
    try:
        subprocess.run([
            "alembic", "revision", "--autogenerate", "-m", "initial_schema"
        ], check=True)
        print("[migration] Initial migration generated successfully.")
        
        print("[migration] Applying migration to database...")
        subprocess.run([
            "alembic", "upgrade", "head"
        ], check=True)
        print("[migration] Database is now up to date.")
        
    except subprocess.CalledProcessError as e:
        print(f"[migration] Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
