# Two rules pytest follows: files must be named test_*.py, and functions must start with test_.
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_read_entry(client):
    created = client.post(
        "/api/v1/entries",
        json={
            "title": "Test entry",
            "content": "Some content.",
            "mood": 4,
            "entry_date": "2026-08-11",
        },
    )
    entry_id = created.json()["id"]

    response = client.get(f"/api/v1/entries/{entry_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Test entry"


def test_list_entries(client):
    client.post(
        "/api/v1/entries",
        json={
            "title": "Test entry",
            "content": "Some content.",
            "mood": 4,
            "entry_date": "2026-08-11",
        },
    )
    client.post(
        "/api/v1/entries",
        json={
            "title": "Test entry",
            "content": "Some content.",
            "mood": 4,
            "entry_date": "2026-08-11",
        },
    )

    response = client.get("/api/v1/entries")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_delete_entry(client):
    created = client.post(
        "/api/v1/entries",
        json={
            "title": "Test entry",
            "content": "Some content.",
            "mood": 4,
            "entry_date": "2026-08-11",
        },
    )
    entry_id = created.json()["id"]

    response = client.delete(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 204

    after = client.get(f"/api/v1/entries/{entry_id}")
    assert after.status_code == 404


def test_read_missing_entry_returns_404(client):
    response = client.get("/api/v1/entries/9999")
    assert response.status_code == 404


def test_create_entry_rejects_bad_mood(client):
    response = client.post(
        "/api/v1/entries",
        json={
            "title": "Test entry",
            "content": "Some content.",
            "mood": 9,
            "entry_date": "2026-08-11",
        },
    )
    assert response.status_code == 422
