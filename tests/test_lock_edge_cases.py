# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from unittest.mock import MagicMock

import pytest
from coreason_identity.models import UserContext
from pydantic import ValidationError

from coreason_protocol.interfaces import VeritasClient
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


@pytest.fixture
def complex_protocol() -> ProtocolDefinition:
    """Creates a complex protocol with multiple blocks and terms."""
    term_p1 = OntologyTerm(
        id="t-p1", label="Elderly", vocab_source="MeSH", code="D000000", origin=TermOrigin.USER_INPUT
    )
    term_p2 = OntologyTerm(
        id="t-p2", label="Geriatric", vocab_source="MeSH", code="D000001", origin=TermOrigin.SYSTEM_EXPANSION
    )
    block_p = PicoBlock(block_type="P", description="Population", terms=[term_p1, term_p2], logic_operator="OR")

    term_i1 = OntologyTerm(id="t-i1", label="Aspirin", vocab_source="RxNorm", code="1191", origin=TermOrigin.USER_INPUT)
    block_i = PicoBlock(block_type="I", description="Intervention", terms=[term_i1])

    term_o1 = OntologyTerm(id="t-o1", label="Death", vocab_source="MeSH", code="D003643", origin=TermOrigin.USER_INPUT)
    block_o = PicoBlock(block_type="O", description="Outcome", terms=[term_o1])

    return ProtocolDefinition(
        id="proto-complex",
        title="Complex Protocol",
        research_question="Complex Question",
        pico_structure={"P": block_p, "I": block_i, "O": block_o},
    )


def test_lock_veritas_failure(complex_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    """Test that if VeritasClient fails, the protocol remains in DRAFT."""
    mock_veritas = MagicMock(spec=VeritasClient)
    mock_veritas.register_protocol.side_effect = Exception("Veritas Service Down")

    with pytest.raises(Exception, match="Veritas Service Down"):
        complex_protocol.lock(test_context, mock_veritas)

    assert complex_protocol.status == ProtocolStatus.DRAFT
    assert complex_protocol.approval_history is None


def test_lock_complex_payload(complex_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    """Test locking a complex protocol structure."""
    mock_veritas = MagicMock(spec=VeritasClient)
    mock_veritas.register_protocol.return_value = "hash-complex"

    complex_protocol.lock(test_context, mock_veritas)

    assert complex_protocol.status == ProtocolStatus.APPROVED
    assert complex_protocol.approval_history is not None
    assert complex_protocol.approval_history.veritas_hash == "hash-complex"

    # Verify the payload passed to register_protocol contains all data
    call_args = mock_veritas.register_protocol.call_args[0][0]
    assert call_args["id"] == "proto-complex"
    assert "P" in call_args["pico_structure"]
    assert "I" in call_args["pico_structure"]
    assert len(call_args["pico_structure"]["P"]["terms"]) == 2


def test_lock_invalid_hash(complex_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    """Test that locking fails if Veritas returns an empty hash."""
    mock_veritas = MagicMock(spec=VeritasClient)
    mock_veritas.register_protocol.return_value = "   "  # Empty/whitespace

    with pytest.raises(ValidationError, match="veritas_hash cannot be empty"):
        complex_protocol.lock(test_context, mock_veritas)

    # Should remain in DRAFT if validation fails during assignment
    # Note: validation happens when assigning to approval_history.
    # If assignment fails, status assignment happens after, so status should be DRAFT.
    assert complex_protocol.status == ProtocolStatus.DRAFT
