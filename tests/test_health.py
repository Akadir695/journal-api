from app.api.deps import get_redis
from app.main import app

async def test_liveness_always_returns_ok(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_returns_ok_when_dependencies_are_up(client):
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"
    assert response.json()["checks"]["redis"] == "ok"


async def test_readiness_returns_503_when_redis_is_down(client):
    class DeadRedis:
        async def ping(self):
            raise ConnectionError("redis is down")

    app.dependency_overrides[get_redis] = lambda: DeadRedis()
    try:
        response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_redis, None)

    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "unavailable"
    assert response.json()["checks"]["database"] == "ok"