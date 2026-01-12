# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from datetime import datetime
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


class MockVeritasClient:
    """Mock implementation of VeritasClientProtocol for testing."""

    def hash_and_register(self, data: Dict[str, Any]) -> str:
        return "hash_12345"


@pytest.fixture  # type: ignore[misc]
def sample_term_user() -> OntologyTerm:
    return OntologyTerm(
        id="uuid-1", label="Heart Attack", vocab_source="MeSH", code="D009203", origin=TermOrigin.USER_INPUT
    )


@pytest.fixture  # type: ignore[misc]
def sample_term_system() -> OntologyTerm:
    return OntologyTerm(
        id="uuid-2",
        label="Myocardial Infarction",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.SYSTEM_EXPANSION,
    )


@pytest.fixture  # type: ignore[misc]
def sample_pico_structure(sample_term_user: OntologyTerm, sample_term_system: OntologyTerm) -> Dict[str, PicoBlock]:
    return {
        "P": PicoBlock(block_type="P", description="Patient Population", terms=[sample_term_user, sample_term_system])
    }


@pytest.fixture  # type: ignore[misc]
def sample_protocol(sample_pico_structure: Dict[str, PicoBlock]) -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="How to treat heart attacks?",
        pico_structure=sample_pico_structure,
    )


def test_ontology_term_soft_delete(sample_term_user: OntologyTerm) -> None:
    """Test that soft_delete correctly sets is_active and override_reason."""
    assert sample_term_user.is_active is True
    assert sample_term_user.override_reason is None

    reason = "Not relevant"
    sample_term_user.soft_delete(reason)

    assert sample_term_user.is_active is False
    assert sample_term_user.override_reason == reason


def test_protocol_definition_validation_success(sample_protocol: ProtocolDefinition) -> None:
    """Test successful instantiation of ProtocolDefinition."""
    assert sample_protocol.status == ProtocolStatus.DRAFT
    assert sample_protocol.approval_history is None
    assert len(sample_protocol.pico_structure) == 1
    assert sample_protocol.pico_structure["P"].block_type == "P"


def test_protocol_definition_validation_failure() -> None:
    """Test validation failure when dictionary key matches block_type."""
    bad_structure = {
        "P": PicoBlock(
            block_type="I",  # Mismatch: Key is P, Type is I
            description="Intervention",
            terms=[],
        )
    }
    with pytest.raises(ValidationError) as excinfo:
        ProtocolDefinition(id="proto-fail", title="Fail", research_question="?", pico_structure=bad_structure)
    assert "Key 'P' does not match block_type 'I'" in str(excinfo.value)


def test_protocol_lock_workflow(sample_protocol: ProtocolDefinition) -> None:
    """Test the lock method transitions state and records approval."""
    client = MockVeritasClient()
    user_id = "user-1"

    assert sample_protocol.status == ProtocolStatus.DRAFT

    # Act
    locked_protocol = sample_protocol.lock(user_id, client)

    # Assert
    assert locked_protocol.status == ProtocolStatus.APPROVED
    assert locked_protocol.approval_history is not None
    assert locked_protocol.approval_history.approver_id == user_id
    assert locked_protocol.approval_history.veritas_hash == "hash_12345"
    assert isinstance(locked_protocol.approval_history.timestamp, datetime)


def test_render_html(sample_protocol: ProtocolDefinition) -> None:
    """Test the render method produces expected HTML elements."""
    html = sample_protocol.render(format="html")

    assert "<h1>Test Protocol</h1>" in html
    assert "Patient Population" in html

    # Check User Input styling (Bold, Blue)
    assert "color: blue;" in html
    assert "Heart Attack" in html

    # Check System Expansion styling (Italic, Grey)
    assert "color: grey;" in html
    assert "Myocardial Infarction" in html


def test_render_default_format(sample_protocol: ProtocolDefinition) -> None:
    """Test the render method fallback for unknown formats."""
    text = sample_protocol.render(format="text")
    assert "Protocol: Test Protocol (DRAFT)" == text


def test_render_human_injection(sample_protocol: ProtocolDefinition) -> None:
    """Test rendering of human injected terms."""
    injected_term = OntologyTerm(
        id="uuid-3", label="Added by Human", vocab_source="Manual", code="MANUAL", origin=TermOrigin.HUMAN_INJECTION
    )

    # Modify protocol to include injected term
    sample_protocol.pico_structure["P"].terms.append(injected_term)

    html = sample_protocol.render(format="html")

    assert "Added by Human" in html
    assert "(Manual:MANUAL)" in html


def test_render_deleted_term(sample_protocol: ProtocolDefinition) -> None:
    """Test that soft-deleted terms are rendered with strike-through."""
    # Delete one term
    term = sample_protocol.pico_structure["P"].terms[0]
    term.soft_delete("Bad term")

    html = sample_protocol.render(format="html")

    # Check for red strike-through
    assert "color: red; text-decoration: line-through;" in html
