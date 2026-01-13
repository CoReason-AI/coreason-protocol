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
from coreason_protocol.main import hello_world
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)
from pydantic import ValidationError


def test_hello_world() -> None:
    assert hello_world() == "Hello World!"


class TestOntologyTerm:
    def test_valid_ontology_term(self) -> None:
        term = OntologyTerm(
            id="123",
            label="Heart Attack",
            vocab_source="MeSH",
            code="D009203",
            origin=TermOrigin.SYSTEM_EXPANSION,
        )
        assert term.id == "123"
        assert term.label == "Heart Attack"
        assert term.is_active is True

    def test_empty_fields_raise_error(self) -> None:
        with pytest.raises(ValidationError, match="Field cannot be empty"):
            OntologyTerm(
                id="",
                label="Heart Attack",
                vocab_source="MeSH",
                code="D009203",
                origin=TermOrigin.SYSTEM_EXPANSION,
            )


class TestPicoBlock:
    def test_valid_pico_block(self) -> None:
        term = OntologyTerm(
            id="123",
            label="Elderly",
            vocab_source="MeSH",
            code="D000000",
            origin=TermOrigin.USER_INPUT,
        )
        block = PicoBlock(block_type="P", description="Elderly Patients", terms=[term], logic_operator="OR")
        assert block.block_type == "P"
        assert len(block.terms) == 1

    def test_invalid_block_type(self) -> None:
        with pytest.raises(ValidationError, match="block_type must be one of"):
            PicoBlock(
                block_type="X",  # Invalid
                description="Elderly Patients",
                terms=[],
            )

    def test_invalid_logic_operator(self) -> None:
        with pytest.raises(ValidationError, match="logic_operator must be AND, OR, or NOT"):
            PicoBlock(
                block_type="P",
                description="Elderly Patients",
                terms=[],
                logic_operator="XOR",
            )

    def test_empty_description_raises_error(self) -> None:
        with pytest.raises(ValidationError, match="description cannot be empty"):
            PicoBlock(
                block_type="P",
                description="  ",
                terms=[],
            )


class TestProtocolDefinition:
    def test_valid_protocol_definition(self) -> None:
        term = OntologyTerm(
            id="123",
            label="Elderly",
            vocab_source="MeSH",
            code="D000000",
            origin=TermOrigin.USER_INPUT,
        )
        block = PicoBlock(block_type="P", description="Elderly Patients", terms=[term])
        protocol = ProtocolDefinition(
            id="proto-1",
            title="Test Protocol",
            research_question="Question?",
            pico_structure={"P": block},
        )
        assert protocol.status == ProtocolStatus.DRAFT
        assert protocol.pico_structure["P"] == block

        # Test placeholders
        assert protocol.render() == ""

        # Test method stubs / functionality
        protocol.override_term("123", "Reason")
        protocol.inject_term("P", term)

        mock_veritas = MagicMock()
        mock_veritas.register_protocol.return_value = "hash-123"
        assert protocol.lock("user1", mock_veritas) == protocol

    def test_pico_structure_key_mismatch(self) -> None:
        term = OntologyTerm(
            id="123",
            label="Elderly",
            vocab_source="MeSH",
            code="D000000",
            origin=TermOrigin.USER_INPUT,
        )
        block = PicoBlock(block_type="P", description="Elderly Patients", terms=[term])
        with pytest.raises(ValidationError, match="Key mismatch in pico_structure"):
            ProtocolDefinition(
                id="proto-1",
                title="Test Protocol",
                research_question="Question?",
                pico_structure={"I": block},  # Key 'I' != block_type 'P'
            )
