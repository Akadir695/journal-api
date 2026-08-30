async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_entry_returns_201(auth_client):
    response = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["title"] == "x"


async def test_read_entry_returns_200(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    entry_id = created.json()["id"]
    response = await auth_client.get(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "x"


async def test_read_missing_entry_returns_404(auth_client):
    response = await auth_client.get("/api/v1/entries/999999")
    assert response.status_code == 404


async def test_create_entry_invalid_mood_returns_422(auth_client):
    response = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 8, "entry_date": "2026-08-24"},
    )

    assert response.status_code == 422


async def test_patch_entry_updates_only_sent_fields(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    entry_id = created.json()["id"]

    response = await auth_client.patch(
        f"/api/v1/entries/{entry_id}",
        json={"mood": 5},
    )
    assert response.status_code == 200
    assert response.json()["mood"] == 5
    assert response.json()["title"] == "x"


async def test_patch_missing_entry_returns_404(auth_client):
    response = await auth_client.patch(
        "/api/v1/entries/99999",
        json={"mood": 5},
    )

    assert response.status_code == 404


async def test_delete_entry_returns_204(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    entry_id = created.json()["id"]
    response = await auth_client.delete(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 204


async def test_read_deleted_entry_returns_404(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    entry_id = created.json()["id"]
    await auth_client.delete(f"/api/v1/entries/{entry_id}")
    response = await auth_client.get(
        f"/api/v1/entries/{entry_id}",
    )
    assert response.status_code == 404


async def test_list_returns_first_page(auth_client):

    for i in range(25):
        await auth_client.post(
            "/api/v1/entries",
            json={"title": f"Entry {i}", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
        )
    response = await auth_client.get("/api/v1/entries?page=1&size=10")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 10
    assert response.json()["total"] == 25


async def test_list_returns_second_page(auth_client):

    for i in range(25):
        await auth_client.post(
            "/api/v1/entries",
            json={"title": f"Entry {i}", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
        )

    page1 = await auth_client.get("/api/v1/entries?page=1&size=10")
    page2 = await auth_client.get("/api/v1/entries?page=2&size=10")
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 10
    assert page1.json()["items"][0]["id"] != page2.json()["items"][0]["id"]
    assert page2.json()["total"] == 25


async def test_last_page_returns_remainder(auth_client):

    for i in range(25):
        await auth_client.post(
            "/api/v1/entries",
            json={"title": f"Entry {i}", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
        )
    response = await auth_client.get("/api/v1/entries?page=3&size=10")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 5


async def test_page_past_end_returns_empty(auth_client):

    for i in range(25):
        await auth_client.post(
            "/api/v1/entries",
            json={"title": f"Entry {i}", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
        )
    response = await auth_client.get("/api/v1/entries?page=99&size=10")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0


async def test_filter_by_mood_returns_only_that_mood(auth_client):

    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 4, "entry_date": "2026-08-24"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 5, "entry_date": "2026-08-24"},
    )
    response = await auth_client.get("/api/v1/entries?mood=3")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["mood"] == 3


async def test_filter_by_date_range_returns_entries_in_range(auth_client):

    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-01-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 4, "entry_date": "2026-06-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 5, "entry_date": "2026-12-01"},
    )
    response = await auth_client.get("/api/v1/entries?date_from=2026-05-01&date_to=2026-07-01")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["entry_date"] == "2026-06-01"


async def test_sort_by_mood_returns_highest_first(auth_client):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-01-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 1, "entry_date": "2026-06-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 5, "entry_date": "2026-12-01"},
    )

    response = await auth_client.get("/api/v1/entries?sort=mood")
    assert response.status_code == 200
    assert response.json()["items"][0]["mood"] == 5
    assert response.json()["items"][2]["mood"] == 1


async def test_search_by_q_matches_content(auth_client):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "gardening", "mood": 1, "entry_date": "2026-06-01"},
    )

    response = await auth_client.get("/api/v1/entries?q=kubernetes")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert "kubernetes" in response.json()["items"][0]["content"]


async def test_deleted_entry_not_in_list(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "gardening", "mood": 1, "entry_date": "2026-06-01"},
    )
    entry_id = created.json()["id"]

    await auth_client.delete(f"/api/v1/entries/{entry_id}")
    response = await auth_client.get("/api/v1/entries")
    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_restore_brings_entry_back(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "gardening", "mood": 1, "entry_date": "2026-06-01"},
    )
    entry_id = created.json()["id"]

    await auth_client.delete(f"/api/v1/entries/{entry_id}")

    restored = await auth_client.post(f"/api/v1/entries/{entry_id}/restore")
    assert restored.status_code == 204


async def test_restore_live_entry_returns_404(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )

    entry_id = created.json()["id"]

    restored = await auth_client.post(f"/api/v1/entries/{entry_id}/restore")
    assert restored.status_code == 404


async def test_delete_twice_returns_404(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )

    entry_id = created.json()["id"]

    await auth_client.delete(f"/api/v1/entries/{entry_id}")
    response = await auth_client.delete(f"/api/v1/entries/{entry_id}")

    assert response.status_code == 404


async def test_other_user_cannot_read_entry(auth_client, other_client):

    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )

    entry_id = created.json()["id"]
    response = await other_client.get(f"/api/v1/entries/{entry_id}")

    assert response.status_code == 404


async def test_other_user_cannot_delete_entry(auth_client, other_client):

    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )

    entry_id = created.json()["id"]
    response = await other_client.delete(f"/api/v1/entries/{entry_id}")

    assert response.status_code == 404


async def test_other_user_cannot_restore_entry(auth_client, other_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )

    entry_id = created.json()["id"]

    await auth_client.delete(f"/api/v1/entries/{entry_id}")

    restored = await other_client.post(f"/api/v1/entries/{entry_id}/restore")
    assert restored.status_code == 404


async def test_other_user_list_is_empty(auth_client, other_client):
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "kubernetes", "mood": 3, "entry_date": "2026-01-01"},
    )
    await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "gardening", "mood": 1, "entry_date": "2026-06-01"},
    )

    response = await other_client.get("/api/v1/entries")
    assert response.json()["total"] == 0


async def test_create_entry_with_tag_attaches_it(auth_client):
    response = await auth_client.post(
        "/api/v1/entries",
        json={
            "title": "x",
            "content": "y",
            "mood": 3,
            "entry_date": "2026-08-24",
            "tags": ["work"],
        },
    )

    assert response.status_code == 201
    assert len(response.json()["tags"]) == 1
    assert response.json()["tags"][0]["name"] == "work"



async def test_other_user_cannot_see_tags(auth_client, other_client):
    await auth_client.post(
        "/api/v1/entries",
        json={
            "title": "x",
            "content": "y",
            "mood": 3,
            "entry_date": "2026-08-24",
            "tags": ["work"],
        },
    )
    response = await other_client.get('/api/v1/tags')
    assert response.status_code == 200
    assert response.json() == []

async def test_same_tag_name_allowed_for_different_user(auth_client, other_client):
    await auth_client.post(
        "/api/v1/entries",
        json={
            "title": "x",
            "content": "y",
            "mood": 3,
            "entry_date": "2026-08-24",
            "tags": ["work"],
        },
    )
    await other_client.post(
        "/api/v1/entries",
        json={
            "title": "x",
            "content": "y",
            "mood": 3,
            "entry_date": "2026-08-24",
            "tags": ["work"],
        },
    )

    response = await other_client.get("/api/v1/tags")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "work"


async def test_deleting_tag_does_not_delete_entry(auth_client):
    created = await auth_client.post(
        "/api/v1/entries",
        json={
            "title": "x",
            "content": "y",
            "mood": 3,
            "entry_date": "2026-08-24",
            "tags": ["work"],
        },
    )
    entry_id = created.json()["id"]
    tag_id = created.json()["tags"][0]["id"]
    await auth_client.delete(f"/api/v1/tags/{tag_id}")
    response = await auth_client.get(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 200

