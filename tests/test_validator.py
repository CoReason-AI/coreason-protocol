from typing import Dict

import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    TermOrigin,
)
from coreason_protocol.validator import ProtocolValidator


@pytest.fixture
def base_term() -> OntologyTerm:
    return OntologyTerm(
        id="term-1",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )


@pytest.fixture
def valid_pico_structure(base_term: OntologyTerm) -> Dict[str, PicoBlock]:
    return {
        "P": PicoBlock(block_type="P", description="Pop", terms=[base_term]),
        "I": PicoBlock(block_type="I", description="Int", terms=[base_term]),
        "O": PicoBlock(block_type="O", description="Out", terms=[base_term]),
    }


@pytest.fixture
def protocol_definition(valid_pico_structure: Dict[str, PicoBlock]) -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="Question",
        pico_structure=valid_pico_structure,
    )


def test_validator_valid_protocol(protocol_definition: ProtocolDefinition) -> None:
    """Test that a fully valid protocol passes validation."""
    ProtocolValidator.validate(protocol_definition)


def test_validator_missing_required_block(protocol_definition: ProtocolDefinition) -> None:
    """Test that missing P, I, or O block raises ValueError."""
    # Remove 'I' block
    del protocol_definition.pico_structure["I"]

    with pytest.raises(ValueError, match="Missing required block: 'I'"):
        ProtocolValidator.validate(protocol_definition)


def test_validator_empty_block(protocol_definition: ProtocolDefinition) -> None:
    """Test that an empty term list in a required block raises ValueError."""
    # Empty the terms in 'P' block
    protocol_definition.pico_structure["P"].terms = []

    with pytest.raises(ValueError, match="Block 'P' cannot be empty"):
        ProtocolValidator.validate(protocol_definition)


def test_validator_active_term_empty_label(protocol_definition: ProtocolDefinition) -> None:
    """Test that an active term with empty label raises ValueError."""
    term = OntologyTerm.model_construct(
        id="term-bad",
        label="   ",  # whitespace
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
        is_active=True,
    )
    protocol_definition.pico_structure["P"].terms.append(term)

    with pytest.raises(ValueError, match="Active term in block 'P' has empty label"):
        ProtocolValidator.validate(protocol_definition)


def test_validator_active_term_empty_code(protocol_definition: ProtocolDefinition) -> None:
    """Test that an active term with empty code raises ValueError."""
    term = OntologyTerm(
        id="term-bad-code",
        label="Valid Label",
        vocab_source="MeSH",
        code="",  # Empty code
        origin=TermOrigin.USER_INPUT,
        is_active=True,
    )
    protocol_definition.pico_structure["I"].terms.append(term)

    with pytest.raises(ValueError, match="Active term in block 'I' has empty code"):
        ProtocolValidator.validate(protocol_definition)


def test_validator_inactive_term_ignored(protocol_definition: ProtocolDefinition) -> None:
    """Test that inactive terms with invalid fields are ignored."""
    term = OntologyTerm(
        id="term-inactive",
        label="Valid Label",
        vocab_source="MeSH",
        code="",  # Empty code but inactive
        origin=TermOrigin.USER_INPUT,
        is_active=False,
        override_reason="Deleted",
    )
    protocol_definition.pico_structure["O"].terms.append(term)

    # Should pass
    ProtocolValidator.validate(protocol_definition)


def test_validator_optional_blocks_checked(protocol_definition: ProtocolDefinition, base_term: OntologyTerm) -> None:
    """Test that optional blocks (C, S) are also checked for term validity."""
    # Add 'C' block
    protocol_definition.pico_structure["C"] = PicoBlock(block_type="C", description="Comp", terms=[])
    ProtocolValidator.validate(protocol_definition)

    # Now add bad term to C
    term = OntologyTerm(
        id="term-bad-c", label="Label", vocab_source="MeSH", code="", origin=TermOrigin.USER_INPUT, is_active=True
    )
    protocol_definition.pico_structure["C"].terms.append(term)

    with pytest.raises(ValueError, match="Active term in block 'C' has empty code"):
        ProtocolValidator.validate(protocol_definition)


def test_validator_invalid_logic_operator(protocol_definition: ProtocolDefinition) -> None:
    """Test that invalid logic operator raises ValueError."""
    # Use model_construct to bypass Pydantic validation
    block = PicoBlock.model_construct(
        block_type="P", description="Pop", terms=protocol_definition.pico_structure["P"].terms, logic_operator="XOR"
    )
    protocol_definition.pico_structure["P"] = block

    with pytest.raises(ValueError, match="Block 'P' has invalid logic_operator: 'XOR'"):
        ProtocolValidator.validate(protocol_definition)
