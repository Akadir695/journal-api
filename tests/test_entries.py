async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_register_user(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "akadir", "email": "a@test.com", "password": "password123"},
    )
    assert response.status_code == 201


async def test_auth_client_can_create_entry(auth_client):
    response = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    assert response.status_code == 201
