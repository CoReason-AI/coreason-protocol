from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from coreason_protocol.server import app

# We need to patch httpx.AsyncClient used in ProtocolServiceAsync
# ProtocolServiceAsync is initialized in server.lifespan

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "version": "0.1.0", "role": "design_plane"}

def test_draft_protocol():
    with TestClient(app) as client:
        response = client.post("/protocol/draft", json={"question": "Does aspirin prevent cancer?"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DRAFT"
        assert data["research_question"] == "Does aspirin prevent cancer?"
        assert "id" in data

@patch("coreason_protocol.service.httpx.AsyncClient")
def test_lock_protocol(mock_client_cls):
    # Setup mock client instance
    mock_client = AsyncMock()
    # Mock the post return value
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"hash": "veritas-hash-123"}
    mock_client.post.return_value = mock_response

    # Mock context manager methods
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_client_cls.return_value = mock_client

    with TestClient(app) as client:
        # Create a draft first
        draft_resp = client.post("/protocol/draft", json={"question": "test"})
        protocol = draft_resp.json()

        # Populate mandatory blocks for validation
        protocol["pico_structure"] = {
            "P": {"block_type": "P", "description": "Population", "terms": [{"id": "11111111-1111-1111-1111-111111111111", "label": "Adults", "vocab_source": "MeSH", "code": "D000328", "origin": "USER_INPUT", "is_active": True}]},
            "I": {"block_type": "I", "description": "Intervention", "terms": [{"id": "22222222-2222-2222-2222-222222222222", "label": "Aspirin", "vocab_source": "MeSH", "code": "D001241", "origin": "USER_INPUT", "is_active": True}]},
            "O": {"block_type": "O", "description": "Outcome", "terms": [{"id": "33333333-3333-3333-3333-333333333333", "label": "Survival", "vocab_source": "MeSH", "code": "D015996", "origin": "USER_INPUT", "is_active": True}]},
        }

        response = client.post("/protocol/lock", json={"protocol": protocol, "user_id": "user123"})

        if response.status_code != 200:
            print(f"Lock failed: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["approval_history"]["veritas_hash"] == "veritas-hash-123"

def test_compile_protocol():
    with TestClient(app) as client:
        # Create a draft
        draft_resp = client.post("/protocol/draft", json={"question": "test"})
        protocol = draft_resp.json()

        # Populate mandatory blocks to ensure meaningful compilation
        protocol["pico_structure"] = {
            "P": {"block_type": "P", "description": "Population", "terms": [{"id": "11111111-1111-1111-1111-111111111111", "label": "Adults", "vocab_source": "MeSH", "code": "D000328", "origin": "USER_INPUT", "is_active": True}]},
            "I": {"block_type": "I", "description": "Intervention", "terms": [{"id": "22222222-2222-2222-2222-222222222222", "label": "Aspirin", "vocab_source": "MeSH", "code": "D001241", "origin": "USER_INPUT", "is_active": True}]},
            "O": {"block_type": "O", "description": "Outcome", "terms": [{"id": "33333333-3333-3333-3333-333333333333", "label": "Survival", "vocab_source": "MeSH", "code": "D015996", "origin": "USER_INPUT", "is_active": True}]},
        }

        response = client.post("/protocol/compile", json={"protocol": protocol, "target": "PUBMED", "user_id": "user123"})

        if response.status_code != 200:
            print(f"Compile failed: {response.json()}")

        assert response.status_code == 200
        strategies = response.json()
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert strategies[0]["target"] == "PUBMED"
