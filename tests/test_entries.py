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
     response = await   auth_client.delete(f"/api/v1/entries/{entry_id}")
     assert response.status_code == 204


async def test_read_deleted_entry_returns_404(auth_client):
     created = await auth_client.post(
        "/api/v1/entries",
        json={"title": "x", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
    )
     entry_id = created.json()["id"]
     await   auth_client.delete(f"/api/v1/entries/{entry_id}")
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
    response = await auth_client.get(
        '/api/v1/entries?page=1&size=10'
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 10
    assert response.json()["total"] == 25
    
async def test_list_returns_second_page(auth_client):
    
    for i in range(25):
        await auth_client.post(
            "/api/v1/entries",
            json={"title": f"Entry {i}", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
        )
    response = await auth_client.get(
        '/api/v1/entries?page=1&size=10'
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
    response = await auth_client.get(
        '/api/v1/entries?page=3&size=10'
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 5
  
async def test_page_past_end_returns_empty(auth_client):
    
    for i in range(25):
        await auth_client.post(
            "/api/v1/entries",
            json={"title": f"Entry {i}", "content": "y", "mood": 3, "entry_date": "2026-08-24"},
        )
    response = await auth_client.get(
        '/api/v1/entries?page=99&size=10'
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0



    

