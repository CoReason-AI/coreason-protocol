# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from datetime import timezone
from unittest.mock import MagicMock

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


@pytest.fixture
def mock_context() -> UserContext:
    return UserContext(
        user_id="user-1",
        email="test@coreason.ai",
        groups=["researcher"],
        scopes=["*"],
        claims={},
    )


@pytest.fixture
def valid_pico_structure() -> dict[str, PicoBlock]:
    term = OntologyTerm(
        id="term-1",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )
    # Updated to include P, I, O as they are now mandatory
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


@pytest.fixture
def protocol_definition(valid_pico_structure: dict[str, PicoBlock]) -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="What is the effect of X on Y?",
        pico_structure=valid_pico_structure,
    )


def test_lock_happy_path(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test successful transition from DRAFT to APPROVED."""
    veritas_mock = MagicMock(spec=VeritasClient)
    veritas_mock.register_protocol.return_value = "hash-123"

    protocol_definition.lock(context=mock_context, veritas_client=veritas_mock)

    assert protocol_definition.status == ProtocolStatus.APPROVED
    assert protocol_definition.approval_history is not None
    assert protocol_definition.approval_history.approver_id == "user-1"
    assert protocol_definition.approval_history.veritas_hash == "hash-123"
    assert protocol_definition.approval_history.timestamp.tzinfo == timezone.utc

    # Verify veritas was called with correct data
    veritas_mock.register_protocol.assert_called_once()


def test_lock_already_approved(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test locking an already approved protocol raises ValueError."""
    veritas_mock = MagicMock(spec=VeritasClient)
    veritas_mock.register_protocol.return_value = "hash-123"
    protocol_definition.status = ProtocolStatus.APPROVED

    with pytest.raises(ValueError, match="Cannot lock a protocol that is already APPROVED or EXECUTED"):
        protocol_definition.lock(context=mock_context, veritas_client=veritas_mock)


def test_lock_executed(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test locking an executed protocol raises ValueError."""
    veritas_mock = MagicMock(spec=VeritasClient)
    protocol_definition.status = ProtocolStatus.EXECUTED

    with pytest.raises(ValueError, match="Cannot lock a protocol that is already APPROVED or EXECUTED"):
        protocol_definition.lock(context=mock_context, veritas_client=veritas_mock)


def test_lock_empty_pico_structure(mock_context: UserContext) -> None:
    """Test locking a protocol with empty pico structure raises ValueError."""
    empty_proto = ProtocolDefinition(
        id="proto-empty",
        title="Empty Protocol",
        research_question="Empty?",
        pico_structure={},
    )

    veritas_mock = MagicMock(spec=VeritasClient)

    with pytest.raises(ValueError, match="Missing required block:"):
        empty_proto.lock(context=mock_context, veritas_client=veritas_mock)


def test_lock_returns_self(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test that lock returns the instance itself (fluent interface)."""
    veritas_mock = MagicMock(spec=VeritasClient)
    veritas_mock.register_protocol.return_value = "hash-123"

    result = protocol_definition.lock(context=mock_context, veritas_client=veritas_mock)
    assert result is protocol_definition


def test_lock_fails_validation(protocol_definition: ProtocolDefinition, mock_context: UserContext) -> None:
    """Test that lock raises ValueError if structural validation fails."""
    # Remove 'O' block to cause validation failure
    del protocol_definition.pico_structure["O"]

    veritas_mock = MagicMock(spec=VeritasClient)

    with pytest.raises(ValueError, match="Missing required block: 'O'"):
        protocol_definition.lock(context=mock_context, veritas_client=veritas_mock)
