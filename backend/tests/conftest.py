import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def _db_schema() -> None:
    db_file = Path("app.db")
    if db_file.exists():
        db_file.unlink()
    cfg = Config("backend/alembic.ini")
    command.upgrade(cfg, "head")
