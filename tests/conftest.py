import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from redis.asyncio import Redis
from app.api.deps import get_storage
from app.core.storage import BlobProperties
import pytest

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


@pytest_asyncio.fixture(autouse=True)
async def redis_client():
    client = Redis.from_url(settings.test_redis_url, decode_responses=True)
    await client.flushdb()
    app.state.redis = client
    yield client
    await client.aclose()


class FakeArq:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, name, *args):
        self.jobs.append((name, args))




@pytest_asyncio.fixture(autouse=True)
async def arq_client():
    fake = FakeArq()
    app.state.arq = fake
    yield fake


@pytest.fixture
def storage():
    fake = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_storage, None)

class FakeStorage:
    def __init__(self) -> None:
        self.blobs: dict[str, BlobProperties] = {}
        self.deleted: list[str] = []

    def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        return f"https://fake.blob/{path}?sig=upload"

    def read_url(self, path: str, expires_in: int) -> str:
        return f"https://fake.blob/{path}?sig=read"

    async def get_properties(self, path: str) -> BlobProperties | None:
        return self.blobs.get(path)

    async def delete(self, path: str) -> None:
        self.blobs.pop(path, None)
        self.deleted.append(path)


@pytest.fixture
def storage():
    fake = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_storage, None)