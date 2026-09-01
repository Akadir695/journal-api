from datetime import UTC, datetime


async def test_creating_entry_invalidates_stats(auth_client):
    before = await auth_client.get("/api/v1/stats/streak")

    today = datetime.now(UTC).date().isoformat()
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": today},
    )

    after = await auth_client.get("/api/v1/stats/streak")

    assert before.json()["current_streak"] == 0
    assert after.json()["current_streak"] == 1


async def test_stats_cache_is_per_user(auth_client, other_client):
    today = datetime.now(UTC).date().isoformat()
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": today},
    )

    mine = await auth_client.get("/api/v1/stats/streak")
    theirs = await other_client.get("/api/v1/stats/streak")

    assert mine.json()["current_streak"] == 1
    assert theirs.json()["current_streak"] == 0
    assert theirs.json()["last_entry_date"] is None


async def test_stats_cached_on_second_call(auth_client):
    today = datetime.now(UTC).date().isoformat()
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": today},
    )

    first = await auth_client.get("/api/v1/stats/streak")
    second = await auth_client.get("/api/v1/stats/streak")

    assert first.json() == second.json()
