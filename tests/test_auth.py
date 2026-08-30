from app.core.security import create_access_token
import jwt
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from sqlalchemy import select

from app.db.models.user import User

settings = get_settings()


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


async def test_register_duplicate_username_returns_409(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "akadir", "email": "new@test.com", "password": "password123"},
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "akadir", "email": "new@test123.com", "password": "password123"},
    )
    assert response.status_code == 409
    assert "sername" in response.json()["detail"]


async def test_token_for_missing_user_returns_401(client):
    token = create_access_token("999999", 15)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


async def test_token_without_sub_returns_401(client):
    token = create_access_token("999999", 15)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


async def test_inactive_user_returns_401(auth_client, session):
    result = await session.execute(select(User).where(User.email == "tester@test.com"))
    user = result.scalar_one()
    user.is_active = False
    await session.commit()

    response = await auth_client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.status_code == 401


async def test_streak_with_no_entries_returns_zeros(auth_client):
    response = await auth_client.get("/api/v1/stats/streak")

    assert response.status_code == 200
    body = response.json()
    assert body["current_streak"] == 0
    assert body["longest_streak"] == 0
    assert body["last_entry_date"] is None


async def test_two_entries_same_day_count_as_one_day(auth_client):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    response = await auth_client.get("/api/v1/stats/streak")

    assert response.status_code == 200
    body = response.json()
    assert body["longest_streak"] == 1


async def test_soft_deleted_entry_splits_streak(auth_client):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-25"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-26"},
    )
    entry_id = created.json()["id"]
    await auth_client.delete(f"/api/v1/entries/{entry_id}")
    response = await auth_client.get("/api/v1/stats/streak")

    assert response.status_code == 200
    body = response.json()
    assert body["longest_streak"] == 1


async def test_streak_is_scoped_per_user(auth_client, other_client):
    await other_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    await other_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-25"},
    )

    response = await auth_client.get("/api/v1/stats/streak")

    assert response.status_code == 200
    body = response.json()
    assert body["longest_streak"] == 0
    assert body["last_entry_date"] is None


async def test_summary_is_scoped_per_user(auth_client, other_client):
    await other_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    await other_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-25"},
    )

    response = await auth_client.get("/api/v1/stats/summary?year=2026")

    assert response.status_code == 200
    body = response.json()
    assert body["total_entries"] == 0
    assert len(body["months"]) == 12
