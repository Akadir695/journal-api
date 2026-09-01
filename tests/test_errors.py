from app.core import rate_limit

from app.crud.user import UserCrud


async def test_not_found_returns_problem_details(auth_client):
    response = await auth_client.get("/api/v1/entries/999999")
    body = response.json()
    for field in ("type", "title", "status", "detail", "instance"):
        assert field in body
    assert response.headers["content-type"] == "application/problem+json"
    assert response.status_code == 404


async def test_unauthenticated_returns_problem_details(client):
    response = await client.get("/api/v1/entries")
    body = response.json()
    for field in ("type", "title", "status", "detail", "instance"):
        assert field in body
    assert response.headers["content-type"] == "application/problem+json"
    assert response.status_code == 401


async def test_validation_error_returns_flat_errors(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "akadir", "email": "not-an-email", "password": "password123"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"

    body = response.json()
    assert "errors" in body
    assert body["errors"][0]["field"] == "email"
    assert "message" in body["errors"][0]


async def test_unhandled_error_returns_problem_details(error_client, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("something exploded")

    monkeypatch.setattr("app.main.check_rate_limit", boom)

    response = await error_client.get("/health")

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == 500
    assert "request_id" in body
    assert "something exploded" not in str(body)
