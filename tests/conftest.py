import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()

if not settings.test_database_url or not settings.test_database_url.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must be set and end with _test")


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    connection = await engine.connect()
    transaction = await connection.begin()
    maker = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with maker() as s:
        yield s
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(session):
    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client):
    await client.post(
        "/api/v1/auth/register",
        json={"username": "tester", "email": "tester@test.com", "password": "password123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "tester@test.com", "password": "password123"},
    )
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


# another client
@pytest_asyncio.fixture
async def other_client(session):
    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.post(
            "/api/v1/auth/register",
            json={"username": "other", "email": "other@test.com", "password": "password123"},
        )
        login = await c.post(
            "/api/v1/auth/login",
            data={"username": "other@test.com", "password": "password123"},
        )
        c.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        yield c
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def error_client(session):
    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()