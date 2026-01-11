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
from pydantic import ValidationError

from coreason_protocol.schema import OntologyTerm, PicoBlock, TermOrigin


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


def test_pico_block_invalid_terms() -> None:
    """Test PicoBlock with invalid terms list."""
    with pytest.raises(ValidationError):
        PicoBlock(
            block_type="P",
            description="Patients",
            terms=["Not a term"],
        )
