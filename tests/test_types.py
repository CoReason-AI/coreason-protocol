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

import pytest
from pydantic import ValidationError

from coreason_protocol.types import (
    ApprovalRecord,
    ExecutableStrategy,
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


def test_term_origin_enum() -> None:
    """Verify TermOrigin enum values."""
    assert TermOrigin.USER_INPUT == "USER_INPUT"
    assert TermOrigin.SYSTEM_EXPANSION == "SYSTEM_EXPANSION"
    assert TermOrigin.HUMAN_INJECTION == "HUMAN_INJECTION"


def test_ontology_term_valid() -> None:
    """Verify creating a valid OntologyTerm."""
    term = OntologyTerm(
        id="123", label="Heart Attack", vocab_source="MeSH", code="D009203", origin=TermOrigin.SYSTEM_EXPANSION
    )
    assert term.id == "123"
    assert term.label == "Heart Attack"
    assert term.is_active is True
    assert term.override_reason is None


def test_ontology_term_validation() -> None:
    """Verify validation for missing required fields."""
    with pytest.raises(ValidationError):
        # Missing label, vocab_source, etc.
        # Intentionally invalid to trigger ValidationError
        OntologyTerm.model_validate({"id": "123"})


def test_pico_block_valid() -> None:
    """Verify creating a valid PicoBlock."""
    term = OntologyTerm(
        id="123", label="Heart Attack", vocab_source="MeSH", code="D009203", origin=TermOrigin.SYSTEM_EXPANSION
    )
    block = PicoBlock(block_type="P", description="Patients with Heart Attack", terms=[term])
    assert block.block_type == "P"
    assert len(block.terms) == 1
    assert block.logic_operator == "OR"  # Default check


def test_protocol_status_enum() -> None:
    """Verify ProtocolStatus enum values."""
    assert ProtocolStatus.DRAFT == "DRAFT"
    assert ProtocolStatus.APPROVED == "APPROVED"


def test_executable_strategy_valid() -> None:
    """Verify creating a valid ExecutableStrategy."""
    strategy = ExecutableStrategy(target="PUBMED", query_string="foo AND bar", validation_status="PRESS_PASSED")
    assert strategy.target == "PUBMED"
    assert strategy.query_string == "foo AND bar"


def test_approval_record_valid() -> None:
    """Verify creating a valid ApprovalRecord."""
    now = datetime.now()
    record = ApprovalRecord(approver_id="user_1", timestamp=now, veritas_hash="hash_123")
    assert record.approver_id == "user_1"
    assert record.timestamp == now
    assert record.veritas_hash == "hash_123"


def test_protocol_definition_valid() -> None:
    """Verify creating a valid ProtocolDefinition with defaults."""
    term = OntologyTerm(
        id="123", label="Heart Attack", vocab_source="MeSH", code="D009203", origin=TermOrigin.USER_INPUT
    )
    block = PicoBlock(block_type="P", description="Population", terms=[term])
    protocol = ProtocolDefinition(
        id="proto_1",
        title="My Protocol",
        research_question="What is the effect of X on Y?",
        pico_structure={"P": block},
    )

    assert protocol.id == "proto_1"
    assert protocol.status == ProtocolStatus.DRAFT
    assert protocol.execution_strategies == []
    assert protocol.approval_history is None
    assert protocol.pico_structure["P"] == block


def test_protocol_definition_render_placeholder() -> None:
    """Verify render placeholder returns string."""
    protocol = ProtocolDefinition(id="1", title="Test", research_question="Question", pico_structure={})
    assert protocol.render() == ""


def test_protocol_definition_lock_placeholder() -> None:
    """Verify lock placeholder returns self."""
    protocol = ProtocolDefinition(id="1", title="Test", research_question="Question", pico_structure={})
    locked = protocol.lock("user", None)
    assert locked == protocol
