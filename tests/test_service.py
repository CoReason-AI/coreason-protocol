from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from coreason_identity.models import UserContext

from coreason_protocol.service import ProtocolService, ProtocolServiceAsync
from coreason_protocol.types import OntologyTerm, PicoBlock, ProtocolDefinition, ProtocolStatus, TermOrigin


@pytest.fixture  # type: ignore[misc]
def valid_pico_structure() -> dict[str, PicoBlock]:
    term = OntologyTerm(
        id="term-1",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )
    return {
        "P": PicoBlock(
            block_type="P",
            description="Patients",
            terms=[term],
        ),
        "I": PicoBlock(
            block_type="I",
            description="Intervention",
            terms=[term],
        ),
        "O": PicoBlock(
            block_type="O",
            description="Outcome",
            terms=[term],
        ),
    }


@pytest.fixture  # type: ignore[misc]
def protocol_definition(valid_pico_structure: dict[str, PicoBlock]) -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="What is the effect of X on Y?",
        pico_structure=valid_pico_structure,
    )


@pytest.fixture  # type: ignore[misc]
def mock_context() -> UserContext:
    return UserContext(
        user_id="user-1",
        email="test@coreason.ai",
        groups=["researcher"],
        scopes=["*"],
        claims={},
    )


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lock(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    # Mock the internal client
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"hash": "hash-async-123"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.aclose = MagicMock()

    # We need to set the post method as async
    async def async_post(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    async def async_aclose() -> None:
        pass

    mock_client.post = async_post
    mock_client.aclose = async_aclose

    async with ProtocolServiceAsync(client=mock_client) as svc:
        result = await svc.lock_protocol(protocol_definition, mock_context)

    assert result.status == ProtocolStatus.APPROVED
    assert result.approval_history is not None
    assert result.approval_history.veritas_hash == "hash-async-123"
    assert result.approval_history.approver_id == "user-1"


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lock_validation_error(
    protocol_definition: ProtocolDefinition, mock_context: UserContext
) -> None:
    # Invalid protocol
    del protocol_definition.pico_structure["O"]

    svc = ProtocolServiceAsync()
    with pytest.raises(ValueError, match="Missing required block: 'O'"):
        await svc.lock_protocol(protocol_definition, mock_context)
    await svc.__aexit__(None, None, None)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lock_invalid_state(
    protocol_definition: ProtocolDefinition, mock_context: UserContext
) -> None:
    # Set invalid state
    protocol_definition.status = ProtocolStatus.APPROVED

    svc = ProtocolServiceAsync()
    with pytest.raises(ValueError, match="Cannot lock a protocol that is already APPROVED or EXECUTED"):
        await svc.lock_protocol(protocol_definition, mock_context)
    await svc.__aexit__(None, None, None)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lock_pending_review(
    protocol_definition: ProtocolDefinition, mock_context: UserContext
) -> None:
    # Set pending review state - should raise specific error
    protocol_definition.status = ProtocolStatus.PENDING_REVIEW

    svc = ProtocolServiceAsync()
    with pytest.raises(ValueError, match="Cannot lock protocol in state: .*PENDING_REVIEW"):
        await svc.lock_protocol(protocol_definition, mock_context)
    await svc.__aexit__(None, None, None)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lock_response_variants(
    protocol_definition: ProtocolDefinition, mock_context: UserContext
) -> None:
    # Variant 1: Response is a string
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = "hash-string-123"
    mock_response.raise_for_status = MagicMock()

    async def async_post(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    async def async_aclose() -> None:
        pass

    mock_client.post = async_post
    mock_client.aclose = async_aclose

    async with ProtocolServiceAsync(client=mock_client) as svc:
        result = await svc.lock_protocol(protocol_definition, mock_context)
        assert result.approval_history is not None
        assert result.approval_history.veritas_hash == "hash-string-123"

    # Variant 2: Response is unknown dict
    protocol_definition.status = ProtocolStatus.DRAFT  # Reset
    mock_response.json.return_value = {"other": "value"}

    async with ProtocolServiceAsync(client=mock_client) as svc:
        result = await svc.lock_protocol(protocol_definition, mock_context)
        assert result.approval_history is not None
        assert result.approval_history.veritas_hash == "{'other': 'value'}"


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lock_http_error(
    protocol_definition: ProtocolDefinition, mock_context: UserContext
) -> None:
    # Mock client to raise HTTPError
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.aclose = MagicMock()

    async def async_post(*args: Any, **kwargs: Any) -> None:
        raise httpx.HTTPError("Simulated Network Error")

    async def async_aclose() -> None:
        pass

    mock_client.post = async_post
    mock_client.aclose = async_aclose

    async with ProtocolServiceAsync(client=mock_client) as svc:
        with pytest.raises(RuntimeError, match="Failed to register with Veritas"):
            await svc.lock_protocol(protocol_definition, mock_context)


def test_service_sync_lock(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    # Mock client
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"hash": "hash-sync-123"}
    mock_response.raise_for_status = MagicMock()

    async def async_post(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    async def async_aclose() -> None:
        pass

    mock_client.post = async_post
    mock_client.aclose = async_aclose

    with ProtocolService(client=mock_client) as svc:
        result = svc.lock_protocol(protocol_definition, mock_context)

    assert result.status == ProtocolStatus.APPROVED
    assert result.approval_history is not None
    assert result.approval_history.veritas_hash == "hash-sync-123"


def test_service_sync_multiple_calls(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test that multiple calls in one session work (loop reuse)."""
    # Mock client
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"hash": "hash-sync-multi"}
    mock_response.raise_for_status = MagicMock()

    async def async_post(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    async def async_aclose() -> None:
        pass

    mock_client.post = async_post
    mock_client.aclose = async_aclose

    with ProtocolService(client=mock_client) as svc:
        # First call
        svc.lock_protocol(protocol_definition, mock_context)
        # Reset protocol status for second call (hacky, but simulates new call)
        protocol_definition.status = ProtocolStatus.DRAFT
        # Second call - should not crash if loop is persistent
        svc.lock_protocol(protocol_definition, mock_context)

        # Also check compilation
        svc.compile_protocol(protocol_definition, "PUBMED", mock_context)

    assert protocol_definition.approval_history is not None
    assert protocol_definition.approval_history.approver_id == "user-1"


def test_service_sync_resource_cleanup() -> None:
    mock_client = MagicMock(spec=httpx.AsyncClient)
    aclose_called = False

    async def async_aclose() -> None:
        nonlocal aclose_called
        aclose_called = True

    mock_client.aclose = async_aclose

    # We must mock that internal_client is TRUE in service, otherwise aclose is NOT called.
    # ProtocolServiceAsync logic: if self._internal_client: await self._client.aclose()
    # Constructor: self._internal_client = client is None
    # Here we are passing a client, so internal_client is False, so aclose is NOT called by default.
    # This is correct behavior (dependency injection means caller owns lifecycle).

    # To test cleanup, we should NOT pass a client, but then we can't assert on the mock easily
    # unless we patch httpx.AsyncClient.

    with pytest.raises(AssertionError):
        # Expect failure because we passed a client, so service won't close it
        with ProtocolService(client=mock_client):
            pass
        assert aclose_called

    # Now test with internal client (implicit creation)
    # We need to patch httpx.AsyncClient
    with pytest.MonkeyPatch.context() as m:
        m.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))
        # When client is NOT passed, internal_client=True
        with ProtocolService(client=None):
            pass
        assert aclose_called


def test_service_sync_usage_error(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test that calling methods without 'with' raises RuntimeError."""
    svc = ProtocolService()

    with pytest.raises(RuntimeError, match="ProtocolService must be used as a context manager"):
        svc.lock_protocol(protocol_definition, mock_context)

    with pytest.raises(RuntimeError, match="ProtocolService must be used as a context manager"):
        svc.compile_protocol(protocol_definition, "PUBMED", mock_context)


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_compile(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    async with ProtocolServiceAsync() as svc:
        strategies = await svc.compile_protocol(protocol_definition, "PUBMED", mock_context)

    assert len(strategies) == 1
    assert strategies[0].target == "PUBMED"
    # Note: Compiler generates "Heart Attack"[Mesh], not the code D009203
    # Based on existing PubMedCompiler implementation:
    # if term.vocab_source == VocabSource.MESH.value: return f'"{label}"[Mesh]'
    # It does NOT use the code.
    assert "Heart Attack" in strategies[0].query_string


def test_service_sync_compile(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    with ProtocolService() as svc:
        strategies = svc.compile_protocol(protocol_definition, "PUBMED", mock_context)

    assert len(strategies) == 1
    assert strategies[0].target == "PUBMED"
