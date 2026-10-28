"""Local development launcher: python3 app.py."""
import os
from pathlib import Path
import subprocess
import sys

import uvicorn
from alembic import command
from alembic.config import Config


def main():
    backend = Path(__file__).resolve().parent
    os.chdir(backend)
    command.upgrade(Config(str(backend / "alembic.ini")), "head")
    # Automatically prepare demo identities only for the default local database.
    if not os.getenv("DATABASE_URL"):
        subprocess.run([
            sys.executable, str(backend.parent / "scripts" / "seed_demo_company.py"),
            "--output", str(backend.parent / "infrastructure" / "demo-credentials.json"),
        ], check=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True,
                reload_dirs=[str(backend / "app")])


if __name__ == "__main__":
    main()
