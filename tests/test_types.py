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


def test_render_html_escaping(sample_protocol: ProtocolDefinition) -> None:
    """Test that special characters in terms are escaped in HTML output to prevent XSS."""
    malicious_term = OntologyTerm(
        id="uuid-xss",
        label="<script>alert('XSS')</script>",
        vocab_source="MeSH",
        code="D00000",
        origin=TermOrigin.USER_INPUT,
    )
    sample_protocol.pico_structure["P"].terms.append(malicious_term)

    html = sample_protocol.render(format="html")

    # Should NOT contain raw script tags
    assert "<script>" not in html
    # Should contain escaped version
    assert "&lt;script&gt;" in html or "&#60;script&#62;" in html


def test_render_empty_blocks(sample_protocol: ProtocolDefinition) -> None:
    """Test rendering when blocks have no terms."""
    sample_protocol.pico_structure["P"].terms = []

    html = sample_protocol.render(format="html")

    assert "Patient Population" in html
    assert "<ul>" in html
    assert "</ul>" in html
    # Should be empty list
    assert "<li" not in html


def test_lock_invalid_state(sample_protocol: ProtocolDefinition) -> None:
    """Test locking a protocol that is already approved or executed."""
    client = MockVeritasClient()
    user_id = "user-1"

    # First lock (valid)
    sample_protocol.lock(user_id, client)
    assert sample_protocol.status == ProtocolStatus.APPROVED

    # Second lock (invalid state)
    # The requirement is ambiguous ("must verify strict transitions").
    # Current implementation might be a no-op or raise error.
    # Let's assume strictness implies raising an error or at least not re-hashing.
    # For now, let's just verify it remains APPROVED and doesn't crash,
    # or if we implement strict checks, we expect a ValueError.
    # Given the previous code just did `pass`, it likely stays APPROVED.

    # Let's update the expectation: it should probably raise an error in a rigorous system.
    # I will assert that it raises ValueError after I update the code.
    with pytest.raises(ValueError, match="Cannot lock protocol in state"):
        sample_protocol.lock(user_id, client)


def test_complex_full_pico_lifecycle() -> None:
    """Test a full lifecycle with mixed term origins and soft deletes."""
    # 1. Draft
    terms = [
        OntologyTerm(id="1", label="Aspirin", vocab_source="RxNorm", code="1191", origin=TermOrigin.USER_INPUT),
        OntologyTerm(
            id="2",
            label="Acetylsalicylic Acid",
            vocab_source="RxNorm",
            code="1191",
            origin=TermOrigin.SYSTEM_EXPANSION,
        ),
        OntologyTerm(id="3", label="Tylenol", vocab_source="RxNorm", code="2024", origin=TermOrigin.SYSTEM_EXPANSION),
    ]

    pico = {"I": PicoBlock(block_type="I", description="Interventions", terms=terms)}

    proto = ProtocolDefinition(
        id="complex-1", title="Complex Study", research_question="Aspirin vs Placebo", pico_structure=pico
    )

    assert proto.status == ProtocolStatus.DRAFT

    # 2. Modify (Soft Delete Tylenol)
    proto.pico_structure["I"].terms[2].soft_delete("Wrong drug")

    # 3. Inject Term
    proto.pico_structure["I"].terms.append(
        OntologyTerm(id="4", label="Bufferin", vocab_source="Manual", code="MAN-01", origin=TermOrigin.HUMAN_INJECTION)
    )

    # 4. Render check
    html = proto.render()
    assert "Aspirin" in html
    assert "color: red" in html  # Deleted Tylenol
    assert "Bufferin" in html

    # 5. Lock
    client = MockVeritasClient()
    proto.lock("admin", client)

    assert proto.status == ProtocolStatus.APPROVED  # type: ignore[comparison-overlap]
    assert proto.approval_history is not None
