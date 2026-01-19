# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from typing import Dict

import pytest
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    TermOrigin,
)
from coreason_protocol.validator import ProtocolValidator


@pytest.fixture  # type: ignore[misc]
def base_term() -> OntologyTerm:
    return OntologyTerm(
        id="term-1",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )


@pytest.fixture  # type: ignore[misc]
def kitchen_sink_structure() -> Dict[str, PicoBlock]:
    """
    Creates a complex PICO structure with P, I, C, O, S blocks,
    mixed term origins, and active/inactive terms.
    """
    # Population: Mixed User/System
    p_terms = [
        OntologyTerm(id="p-1", label="Adults", vocab_source="MeSH", code="D000328", origin=TermOrigin.USER_INPUT),
        OntologyTerm(
            id="p-2", label="Middle Aged", vocab_source="MeSH", code="D008875", origin=TermOrigin.SYSTEM_EXPANSION
        ),
    ]

    # Intervention: Human Injection
    i_terms = [
        OntologyTerm(id="i-1", label="Aspirin", vocab_source="RxNorm", code="1191", origin=TermOrigin.HUMAN_INJECTION)
    ]

    # Comparator: Contains an inactive term
    c_terms = [
        OntologyTerm(id="c-1", label="Placebo", vocab_source="MeSH", code="D010919", origin=TermOrigin.USER_INPUT),
        OntologyTerm(
            id="c-2",
            label="Sugar Pill",
            vocab_source="FreeText",
            code="FT001",
            origin=TermOrigin.SYSTEM_EXPANSION,
            is_active=False,
            override_reason="Redundant",
        ),
    ]

    # Outcome: Standard
    o_terms = [
        OntologyTerm(id="o-1", label="Mortality", vocab_source="MeSH", code="D009026", origin=TermOrigin.USER_INPUT)
    ]

    # Study Design: Optional block
    s_terms = [
        OntologyTerm(
            id="s-1",
            label="Randomized Controlled Trial",
            vocab_source="MeSH",
            code="D016449",
            origin=TermOrigin.USER_INPUT,
        )
    ]

    return {
        "P": PicoBlock(block_type="P", description="Population", terms=p_terms, logic_operator="OR"),
        "I": PicoBlock(block_type="I", description="Intervention", terms=i_terms, logic_operator="AND"),
        "C": PicoBlock(block_type="C", description="Comparator", terms=c_terms, logic_operator="OR"),
        "O": PicoBlock(block_type="O", description="Outcome", terms=o_terms, logic_operator="OR"),
        "S": PicoBlock(block_type="S", description="Study Design", terms=s_terms, logic_operator="OR"),
    }


def test_complex_kitchen_sink(kitchen_sink_structure: Dict[str, PicoBlock]) -> None:
    """Test validation of a fully populated, complex protocol."""
    protocol = ProtocolDefinition(
        id="proto-kitchen-sink",
        title="Complex Protocol",
        research_question="Complex Question?",
        pico_structure=kitchen_sink_structure,
    )
    ProtocolValidator.validate(protocol)


def test_logic_operator_case_sensitivity(kitchen_sink_structure: Dict[str, PicoBlock]) -> None:
    """Test that lowercase logic operators fail validation."""
    # Modify 'P' block to have lowercase 'or'
    # Use model_construct to bypass Pydantic enum/validation checks
    bad_block = PicoBlock.model_construct(
        block_type="P",
        description="Population",
        terms=kitchen_sink_structure["P"].terms,
        logic_operator="or",  # Invalid case
    )
    kitchen_sink_structure["P"] = bad_block

    protocol = ProtocolDefinition(
        id="proto-bad-logic", title="Bad Logic", research_question="Q", pico_structure=kitchen_sink_structure
    )

    with pytest.raises(ValueError, match="Block 'P' has invalid logic_operator: 'or'"):
        ProtocolValidator.validate(protocol)


def test_unicode_and_special_chars(base_term: OntologyTerm) -> None:
    """Test that terms with Unicode characters are accepted."""
    unicode_term = OntologyTerm(
        id="u-1",
        label="Naïve T-Cells (CD4+)",  # Special chars
        vocab_source="MeSH",
        code="D000072",
        origin=TermOrigin.USER_INPUT,
    )
    emoji_term = OntologyTerm(
        id="u-2",
        label="Heart 🫀",  # Emoji
        vocab_source="Custom",
        code="CUST-01",
        origin=TermOrigin.HUMAN_INJECTION,
    )

    structure = {
        "P": PicoBlock(block_type="P", description="Pop", terms=[unicode_term]),
        "I": PicoBlock(block_type="I", description="Int", terms=[emoji_term]),
        "O": PicoBlock(block_type="O", description="Out", terms=[base_term]),
    }

    protocol = ProtocolDefinition(
        id="proto-unicode", title="Unicode Protocol", research_question="Q", pico_structure=structure
    )

    # Should pass without error
    ProtocolValidator.validate(protocol)


def test_empty_optional_blocks(base_term: OntologyTerm) -> None:
    """Test that optional blocks (C, S) can be empty."""
    # P, I, O are populated
    structure = {
        "P": PicoBlock(block_type="P", description="Pop", terms=[base_term]),
        "I": PicoBlock(block_type="I", description="Int", terms=[base_term]),
        "O": PicoBlock(block_type="O", description="Out", terms=[base_term]),
        "C": PicoBlock(block_type="C", description="Comp", terms=[]),  # Empty Optional
    }

    protocol = ProtocolDefinition(
        id="proto-optional-empty", title="Optional Empty", research_question="Q", pico_structure=structure
    )

    # Should pass validation as strictness only applies to P, I, O
    ProtocolValidator.validate(protocol)


def test_whitespace_code(base_term: OntologyTerm) -> None:
    """Test that a term with whitespace-only code fails validation."""
    bad_term = OntologyTerm(
        id="bad-code",
        label="Valid Label",
        vocab_source="MeSH",
        code="   \t",  # Whitespace
        origin=TermOrigin.USER_INPUT,
    )

    structure = {
        "P": PicoBlock(block_type="P", description="Pop", terms=[base_term]),
        "I": PicoBlock(block_type="I", description="Int", terms=[bad_term]),
        "O": PicoBlock(block_type="O", description="Out", terms=[base_term]),
    }

    protocol = ProtocolDefinition(
        id="proto-whitespace", title="Whitespace Code", research_question="Q", pico_structure=structure
    )

    with pytest.raises(ValueError, match="Active term in block 'I' has empty code"):
        ProtocolValidator.validate(protocol)


def test_large_payload_performance(base_term: OntologyTerm) -> None:
    """
    Test validation with a large number of terms to check for basic stability.
    Not a rigorous perf test, but sanity check.
    """
    many_terms = []
    for i in range(1000):
        # reuse base_term but unique ids? Validator doesn't check id uniqueness (types.py does)
        # We just check iteration speed/crash
        t = base_term.model_copy()
        t.id = f"term-{i}"
        many_terms.append(t)

    structure = {
        "P": PicoBlock(block_type="P", description="Large Pop", terms=many_terms),
        "I": PicoBlock(block_type="I", description="Int", terms=[base_term]),
        "O": PicoBlock(block_type="O", description="Out", terms=[base_term]),
    }

    protocol = ProtocolDefinition(
        id="proto-large", title="Large Protocol", research_question="Q", pico_structure=structure
    )

    # Should run quickly and pass
    ProtocolValidator.validate(protocol)


def test_validator_case_mismatch(kitchen_sink_structure: Dict[str, PicoBlock]) -> None:
    """
    Test that lowercase keys in pico_structure (e.g., 'p') are treated as
    missing required blocks (since validator expects 'P').
    """
    # Construct a protocol with lowercase keys
    # We must use model_construct because Pydantic validator in types.py
    # enforces key == block.block_type.

    # Create a structure where key is 'p' but block_type is 'P' (or 'p')
    # If we map 'p' -> Block('P'), Pydantic would raise "Key mismatch".
    # We bypass Pydantic.

    bad_structure = {
        "p": kitchen_sink_structure["P"],  # key mismatch
        "I": kitchen_sink_structure["I"],
        "O": kitchen_sink_structure["O"],
    }

    protocol = ProtocolDefinition.model_construct(
        id="proto-case",
        title="Case Mismatch",
        research_question="Q",
        pico_structure=bad_structure,
    )

    # Validator looks for "P". It won't find it.
    with pytest.raises(ValueError, match="Missing required block: 'P'"):
        ProtocolValidator.validate(protocol)
