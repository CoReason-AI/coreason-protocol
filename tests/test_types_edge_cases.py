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
    TermOrigin,
)
from pydantic import ValidationError


def test_validate_assignment_pico_structure() -> None:
    """Verify that assigning an invalid pico_structure after init raises validation error."""
    term = OntologyTerm(id="t1", label="Term", vocab_source="Src", code="C1", origin=TermOrigin.USER_INPUT)
    block_p = PicoBlock(block_type="P", description="Pop", terms=[term])

    protocol = ProtocolDefinition(id="1", title="Title", research_question="Q", pico_structure={"P": block_p})

    # Valid assignment
    protocol.pico_structure = {"P": block_p}

    # Invalid assignment: Key mismatch
    with pytest.raises(ValidationError, match="Key mismatch in pico_structure"):
        protocol.pico_structure = {"I": block_p}


def test_enum_case_sensitivity() -> None:
    """Verify strict enum validation."""
    # TermOrigin is a string enum, so "USER_INPUT" is valid
    OntologyTerm(id="t1", label="Term", vocab_source="Src", code="C1", origin=TermOrigin.USER_INPUT)

    # Passing lowercase "user_input" should fail strict validation unless coercible?
    # Pydantic v2 strict mode (implicit via type) usually requires exact match for str enums or coercible strings.
    # But usually "user_input" != "USER_INPUT".

    with pytest.raises(ValidationError):
        OntologyTerm(
            id="t1",
            label="Term",
            vocab_source="Src",
            code="C1",
            origin="user_input",
        )


def test_deep_validation_failure() -> None:
    """Verify that validation errors in deep structures bubble up."""
    # JSON payload with invalid TermOrigin deep inside
    invalid_json = """
    {
        "id": "1",
        "title": "Title",
        "research_question": "Q",
        "pico_structure": {
            "P": {
                "block_type": "P",
                "description": "Pop",
                "terms": [
                    {
                        "id": "t1",
                        "label": "Term",
                        "vocab_source": "Src",
                        "code": "C1",
                        "origin": "INVALID_ORIGIN"
                    }
                ]
            }
        }
    }
    """
    with pytest.raises(ValidationError) as exc:
        ProtocolDefinition.model_validate_json(invalid_json)

    assert "Input should be 'USER_INPUT', 'SYSTEM_EXPANSION' or 'HUMAN_INJECTION'" in str(exc.value)


def test_malicious_string_payload() -> None:
    """Verify that models accept malicious strings (checking data integrity, not sanitization)."""
    malicious_label = "<script>alert('xss')</script>"
    term = OntologyTerm(id="bad1", label=malicious_label, vocab_source="Src", code="C1", origin=TermOrigin.USER_INPUT)
    assert term.label == malicious_label

    # Ensure it serializes correctly
    json_out = term.model_dump_json()
    assert malicious_label in json_out

    # Ensure it deserializes correctly
    term2 = OntologyTerm.model_validate_json(json_out)
    assert term2.label == malicious_label


def test_validate_assignment_ontology_term() -> None:
    """Verify validate_assignment works on simple fields."""
    term = OntologyTerm(id="t1", label="Valid", vocab_source="Src", code="C1", origin=TermOrigin.USER_INPUT)

    # Valid update
    term.label = "Valid 2"

    # Invalid update (empty string) - check_non_empty validator
    with pytest.raises(ValidationError, match="Field cannot be empty"):
        term.label = "   "


def test_invalid_logic_operator_assignment() -> None:
    """Verify invalid logic operator assignment."""
    term = OntologyTerm(id="t1", label="Term", vocab_source="Src", code="C1", origin=TermOrigin.USER_INPUT)
    block = PicoBlock(block_type="P", description="Pop", terms=[term], logic_operator="OR")

    with pytest.raises(ValidationError, match="logic_operator must be AND, OR, or NOT"):
        block.logic_operator = "XOR"
