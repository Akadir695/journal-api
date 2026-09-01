async def test_rate_limit_returns_429(client):
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.com", "password": "wrong"},
        )

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "wrong"},
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    

async def test_rate_limit_headers_present(client):
    response = await client.get("/health")

    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    
async def test_security_headers_present(client):
    response = await client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"