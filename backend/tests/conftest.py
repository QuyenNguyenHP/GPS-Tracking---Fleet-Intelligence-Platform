import os
from pathlib import Path
import tempfile
import sys

os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tempfile.mkdtemp()) / "test.db")

import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from seed_demo_company import seed


@pytest.fixture()
def client(tmp_path):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed(2, tmp_path / "credentials.json")
    import json
    credentials = json.loads((tmp_path / "credentials.json").read_text())
    with TestClient(app) as test_client:
        yield test_client, credentials
