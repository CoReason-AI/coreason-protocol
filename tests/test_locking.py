from unittest.mock import Mock

import pytest
from coreason_identity.models import UserContext

from coreason_protocol.interfaces import VeritasClient
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


def test_lock_success(test_context: UserContext) -> None:
    # Setup
    term = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.USER_INPUT)
    block_p = PicoBlock(block_type="P", description="Pop", terms=[term])
    block_i = PicoBlock(block_type="I", description="Int", terms=[term])
    block_o = PicoBlock(block_type="O", description="Out", terms=[term])
    pd = ProtocolDefinition(
        id="proto-1",
        title="Test",
        research_question="Q",
        pico_structure={"P": block_p, "I": block_i, "O": block_o},
        status=ProtocolStatus.DRAFT,
    )

    # Mock Veritas
    mock_veritas = Mock(spec=VeritasClient)
    mock_veritas.register_protocol.return_value = "hash_123"

    # Action
    pd.lock(context=test_context, veritas_client=mock_veritas)

    # Assert
    assert pd.status == ProtocolStatus.APPROVED
    assert pd.approval_history is not None
    assert pd.approval_history.approver_id == "test-user"
    assert pd.approval_history.veritas_hash == "hash_123"
    assert pd.approval_history.timestamp is not None

    # Verify mock call
    mock_veritas.register_protocol.assert_called_once()
    call_arg = mock_veritas.register_protocol.call_args[0][0]
    assert call_arg["id"] == "proto-1"
    assert call_arg["status"] == "DRAFT"


def test_lock_fail_wrong_status(test_context: UserContext) -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.APPROVED)
    mock_veritas = Mock()

    # Updated expectation to match new implementation which matches existing tests
    with pytest.raises(ValueError, match="Cannot lock a protocol that is already APPROVED or EXECUTED"):
        pd.lock(test_context, mock_veritas)

    mock_veritas.register_protocol.assert_not_called()


def test_lock_fail_empty_pico(test_context: UserContext) -> None:
    pd = ProtocolDefinition(
        id="1",
        title="T",
        research_question="Q",
        pico_structure={},  # Empty
        status=ProtocolStatus.DRAFT,
    )
    mock_veritas = Mock()

    # Updated expectation: Now handled by Validator
    with pytest.raises(ValueError, match="Missing required block:"):
        pd.lock(test_context, mock_veritas)

    mock_veritas.register_protocol.assert_not_called()


def test_lock_pending_review(test_context: UserContext) -> None:
    """Test locking a protocol in PENDING_REVIEW raises ValueError."""
    term = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.USER_INPUT)
    block = PicoBlock(block_type="P", description="Pop", terms=[term])
    pd = ProtocolDefinition(
        id="1", title="T", research_question="Q", pico_structure={"P": block}, status=ProtocolStatus.PENDING_REVIEW
    )
    mock_veritas = Mock()

    with pytest.raises(ValueError, match="Cannot lock protocol in state: .*PENDING_REVIEW"):
        pd.lock(test_context, mock_veritas)
