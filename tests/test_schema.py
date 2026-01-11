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

from coreason_protocol.schema import (
    ApprovalRecord,
    ExecutableStrategy,
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


# Existing Tests for TermOrigin, OntologyTerm, PicoBlock
def test_term_origin_enum() -> None:
    """Test TermOrigin enum values."""
    assert TermOrigin.USER_INPUT == "USER_INPUT"
    assert TermOrigin.SYSTEM_EXPANSION == "SYSTEM_EXPANSION"
    assert TermOrigin.HUMAN_INJECTION == "HUMAN_INJECTION"


def test_ontology_term_valid() -> None:
    """Test OntologyTerm with valid data."""
    term = OntologyTerm(
        id="123",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )
    assert term.id == "123"
    assert term.label == "Heart Attack"
    assert term.vocab_source == "MeSH"
    assert term.code == "D009203"
    assert term.origin == TermOrigin.USER_INPUT
    assert term.is_active is True
    assert term.override_reason is None


def test_ontology_term_optional_fields() -> None:
    """Test OntologyTerm with optional fields provided."""
    term = OntologyTerm(
        id="123",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.SYSTEM_EXPANSION,
        is_active=False,
        override_reason="Too broad",
    )
    assert term.is_active is False
    assert term.override_reason == "Too broad"


def test_ontology_term_invalid_origin() -> None:
    """Test OntologyTerm with invalid origin."""
    with pytest.raises(ValidationError):
        OntologyTerm(
            id="123",
            label="Heart Attack",
            vocab_source="MeSH",
            code="D009203",
            origin="INVALID_ORIGIN",
        )


def test_ontology_term_empty_string_fields() -> None:
    """Test OntologyTerm fails with empty string fields."""
    with pytest.raises(ValidationError) as exc:
        OntologyTerm(
            id="",
            label="  ",
            vocab_source="",
            code="  ",
            origin=TermOrigin.USER_INPUT,
        )
    errors = exc.value.errors()
    failed_fields = {e["loc"][0] for e in errors}
    assert "id" in failed_fields
    assert "label" in failed_fields
    assert "vocab_source" in failed_fields
    assert "code" in failed_fields


def test_ontology_term_whitespace_only() -> None:
    """Test that whitespace strings are rejected."""
    with pytest.raises(ValidationError):
        OntologyTerm(
            id="123",
            label="   ",  # Invalid
            vocab_source="MeSH",
            code="D1",
            origin=TermOrigin.USER_INPUT,
        )


def test_pico_block_valid() -> None:
    """Test PicoBlock with valid data."""
    term = OntologyTerm(
        id="123",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )
    block = PicoBlock(
        block_type="P",
        description="Patients with Heart Attack",
        terms=[term],
    )
    assert block.block_type == "P"
    assert block.description == "Patients with Heart Attack"
    assert len(block.terms) == 1
    assert block.terms[0] == term
    assert block.logic_operator == "OR"


def test_pico_block_custom_operator() -> None:
    """Test PicoBlock with custom logic operator."""
    block = PicoBlock(
        block_type="I",
        description="Aspirin",
        terms=[],
        logic_operator="AND",
    )
    assert block.logic_operator == "AND"


def test_pico_block_logic_operator_not() -> None:
    """Test PicoBlock with 'NOT' logic operator."""
    block = PicoBlock(
        block_type="P",
        description="Not patients",
        terms=[],
        logic_operator="NOT",
    )
    assert block.logic_operator == "NOT"


def test_pico_block_invalid_values() -> None:
    """Test PicoBlock with invalid enum-like values."""
    with pytest.raises(ValidationError) as exc:
        PicoBlock(
            block_type="X",
            description="   ",
            terms=[],
            logic_operator="MAYBE",
        )
    errors = exc.value.errors()
    failed_fields = {e["loc"][0] for e in errors}
    assert "block_type" in failed_fields
    assert "description" in failed_fields
    assert "logic_operator" in failed_fields


def test_pico_block_invalid_terms() -> None:
    """Test PicoBlock with invalid terms list."""
    with pytest.raises(ValidationError):
        PicoBlock(
            block_type="P",
            description="Patients",
            terms=["Not a term"],
        )


# New Tests for ProtocolStatus, ExecutableStrategy, ApprovalRecord, ProtocolDefinition


def test_protocol_status_enum() -> None:
    """Test ProtocolStatus enum values."""
    assert ProtocolStatus.DRAFT == "DRAFT"
    assert ProtocolStatus.PENDING_REVIEW == "PENDING_REVIEW"
    assert ProtocolStatus.APPROVED == "APPROVED"
    assert ProtocolStatus.EXECUTED == "EXECUTED"


def test_executable_strategy_valid() -> None:
    """Test ExecutableStrategy with valid data."""
    strategy = ExecutableStrategy(
        target="PUBMED",
        query_string='("Heart Attack"[Mesh])',
        validation_status="PRESS_PASSED",
    )
    assert strategy.target == "PUBMED"
    assert strategy.query_string == '("Heart Attack"[Mesh])'
    assert strategy.validation_status == "PRESS_PASSED"


def test_executable_strategy_empty_fields() -> None:
    """Test ExecutableStrategy fails with empty fields."""
    with pytest.raises(ValidationError):
        ExecutableStrategy(
            target="  ",
            query_string="",
            validation_status="PRESS_PASSED",
        )


def test_approval_record_valid() -> None:
    """Test ApprovalRecord with valid data."""
    now = datetime.now()
    record = ApprovalRecord(
        approver_id="user_123",
        timestamp=now,
        veritas_hash="abc123hash",
    )
    assert record.approver_id == "user_123"
    assert record.timestamp == now
    assert record.veritas_hash == "abc123hash"


def test_approval_record_empty_fields() -> None:
    """Test ApprovalRecord fails with empty fields."""
    with pytest.raises(ValidationError):
        ApprovalRecord(
            approver_id="",
            timestamp=datetime.now(),
            veritas_hash="   ",
        )


def test_protocol_definition_valid_minimal() -> None:
    """Test ProtocolDefinition with minimal valid data (DRAFT)."""
    term = OntologyTerm(
        id="t1",
        label="Aspirin",
        vocab_source="RxNorm",
        code="1191",
        origin=TermOrigin.USER_INPUT,
    )
    pico_block = PicoBlock(
        block_type="I",
        description="Intervention",
        terms=[term],
    )

    protocol = ProtocolDefinition(
        id="proto_1",
        title="My Protocol",
        research_question="Does Aspirin work?",
        pico_structure={"I": pico_block},
        execution_strategies=[],
        status=ProtocolStatus.DRAFT,
    )

    assert protocol.id == "proto_1"
    assert protocol.title == "My Protocol"
    assert protocol.research_question == "Does Aspirin work?"
    assert protocol.pico_structure["I"] == pico_block
    assert protocol.execution_strategies == []
    assert protocol.status == ProtocolStatus.DRAFT
    assert protocol.approval_history is None


def test_protocol_definition_full() -> None:
    """Test ProtocolDefinition with all fields populated."""
    term = OntologyTerm(
        id="t1",
        label="Aspirin",
        vocab_source="RxNorm",
        code="1191",
        origin=TermOrigin.USER_INPUT,
    )
    pico_block = PicoBlock(
        block_type="I",
        description="Intervention",
        terms=[term],
    )
    strategy = ExecutableStrategy(
        target="PUBMED",
        query_string="Aspirin",
        validation_status="PRESS_PASSED",
    )
    approval = ApprovalRecord(
        approver_id="u1",
        timestamp=datetime.now(),
        veritas_hash="hash_123",
    )

    protocol = ProtocolDefinition(
        id="proto_1",
        title="Full Protocol",
        research_question="Q?",
        pico_structure={"I": pico_block},
        execution_strategies=[strategy],
        status=ProtocolStatus.APPROVED,
        approval_history=approval,
    )

    assert len(protocol.execution_strategies) == 1
    assert protocol.status == ProtocolStatus.APPROVED
    assert protocol.approval_history == approval


def test_protocol_definition_empty_fields() -> None:
    """Test ProtocolDefinition fails with empty fields."""
    with pytest.raises(ValidationError):
        ProtocolDefinition(
            id="",
            title="  ",
            research_question="",
            pico_structure={},
            execution_strategies=[],
            status=ProtocolStatus.DRAFT,
        )


def test_protocol_definition_method_stubs() -> None:
    """Test that method stubs raise NotImplementedError."""
    protocol = ProtocolDefinition(
        id="proto_1",
        title="Test",
        research_question="Q",
        pico_structure={},
        execution_strategies=[],
        status=ProtocolStatus.DRAFT,
    )

    with pytest.raises(NotImplementedError):
        protocol.render()

    with pytest.raises(NotImplementedError):
        protocol.lock("user", "client")
