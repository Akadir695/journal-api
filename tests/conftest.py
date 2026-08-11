import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.entries import get_crud
from app.crud.entry import EntryCrud
from app.main import app


@pytest.fixture
def client():
    crud = EntryCrud()
    app.dependency_overrides[get_crud] = lambda: crud
    yield TestClient(app)
    app.dependency_overrides.clear()
