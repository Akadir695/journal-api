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
