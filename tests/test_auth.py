from app.core.security import create_access_token


async def test_register_returns_201(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "password123"},
    )

    assert response.status_code == 201
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()


# we are testing  if the email already taken
async def test_register_duplicate_email_returns_409(client):
    payload = {"username": "new", "email": "new@test.com", "password": "password123"}

    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


async def test_register_short_password_returns_422(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "x"},
    )

    assert response.status_code == 422


async def test_register_invalid_email_returns_422(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "1223", "password": "password123"},
    )

    assert response.status_code == 422


async def test_login_returns_tokens(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "password123"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "new@test.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


async def test_login_wrong_password_returns_401(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "password123"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "new@test.com", "password": "password12u3u230"},
    )

    assert response.status_code == 401


async def test_login_unknown_email_returns_401(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "password123"},
    )

    assert response.status_code == 401


async def test_me_without_token_returns_401(client):
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


async def test_me_with_token_returns_current_user(auth_client):
    response = await auth_client.get("/api/v1/users/me")

    assert response.status_code == 200
    assert response.json()["email"] == "tester@test.com"


# we are testing  if the token is expired
async def test_me_with_expired_token_returns_401(client):
    token = create_access_token("1", -1)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


# we are testing  if the is refresh  token
async def test_refresh_returns_new_tokens(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "new@test.com", "password": "password123"},
    )
    old = login.json()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] != old["access_token"]
    assert response.json()["refresh_token"] != old["refresh_token"]


async def test_reused_refresh_token_returns_401(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "new@test.com", "password": "password123"},
    )
    old = login.json()
    await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old["refresh_token"]},
    )
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old["refresh_token"]},
    )
    assert response.status_code == 401


async def test_refresh_after_logout_returns_401(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "new", "email": "new@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "new@test.com", "password": "password123"},
    )
    old = login.json()
    login = await client.post("/api/v1/auth/logout", json={"refresh_token": old["refresh_token"]})
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old["refresh_token"]},
    )

    assert response.status_code == 401
