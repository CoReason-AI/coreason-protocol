# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


# Fixture for a standard valid term
@pytest.fixture
def standard_term() -> OntologyTerm:
    return OntologyTerm(
        id="term-123",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.SYSTEM_EXPANSION,
    )


# Fixture for a standard draft protocol
@pytest.fixture
def draft_protocol(standard_term: OntologyTerm) -> ProtocolDefinition:
    block = PicoBlock(block_type="P", description="Patients", terms=[standard_term], logic_operator="OR")
    return ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="Question?",
        pico_structure={"P": block},
        status=ProtocolStatus.DRAFT,
    )


class TestOverrideTerm:
    def test_override_term_happy_path(self, draft_protocol: ProtocolDefinition) -> None:
        """
        Verify that a term can be successfully soft-deleted in DRAFT status.
        """
        reason = "Too broad"
        draft_protocol.override_term("term-123", reason)

        # Verify the term state
        term = draft_protocol.pico_structure["P"].terms[0]
        assert term.is_active is False
        assert term.override_reason == reason

    def test_override_term_pending_review(self, draft_protocol: ProtocolDefinition) -> None:
        """
        Verify that a term can be overridden in PENDING_REVIEW status.
        """
        draft_protocol.status = ProtocolStatus.PENDING_REVIEW
        reason = "Manual rejection"
        draft_protocol.override_term("term-123", reason)

        term = draft_protocol.pico_structure["P"].terms[0]
        assert term.is_active is False
        assert term.override_reason == reason

    def test_override_term_immutable_state_approved(self, draft_protocol: ProtocolDefinition) -> None:
        """
        Verify that override_term raises RuntimeError if status is APPROVED.
        """
        draft_protocol.status = ProtocolStatus.APPROVED
        with pytest.raises(RuntimeError, match="Cannot modify protocol in APPROVED state"):
            draft_protocol.override_term("term-123", "Reason")

    def test_override_term_immutable_state_executed(self, draft_protocol: ProtocolDefinition) -> None:
        """
        Verify that override_term raises RuntimeError if status is EXECUTED.
        """
        draft_protocol.status = ProtocolStatus.EXECUTED
        with pytest.raises(RuntimeError, match="Cannot modify protocol in EXECUTED state"):
            draft_protocol.override_term("term-123", "Reason")

    def test_override_term_empty_reason(self, draft_protocol: ProtocolDefinition) -> None:
        """
        Verify that an empty or whitespace-only reason raises ValueError.
        """
        with pytest.raises(ValueError, match="Override reason cannot be empty"):
            draft_protocol.override_term("term-123", "   ")

        with pytest.raises(ValueError, match="Override reason cannot be empty"):
            draft_protocol.override_term("term-123", "")

    def test_override_term_missing_id(self, draft_protocol: ProtocolDefinition) -> None:
        """
        Verify that providing a non-existent term_id raises ValueError.
        """
        with pytest.raises(ValueError, match="Term ID 'non-existent' not found in protocol"):
            draft_protocol.override_term("non-existent", "Reason")
