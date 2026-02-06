import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolRequest,
    TermOrigin,
)
from coreason_protocol.validator import ProtocolValidator


# Helper to create a dummy protocol with specific terms
def create_protocol_with_terms(terms: list[str]) -> ProtocolDefinition:
    ontology_terms = []
    for i, label in enumerate(terms):
        ontology_terms.append(
            OntologyTerm(
                id=f"term-{i}",
                label=label,
                vocab_source="MeSH",
                code=f"D00{i}",
                origin=TermOrigin.USER_INPUT,
            )
        )

    # We need P, I, O blocks to satisfy structural checks
    # We will put the terms in 'P' block
    blocks = {
        "P": PicoBlock(block_type="P", description="Pop", terms=ontology_terms),
        "I": PicoBlock(
            block_type="I",
            description="Int",
            terms=[
                OntologyTerm(
                    id="i1",
                    label="Valid",
                    vocab_source="MeSH",
                    code="D1",
                    origin=TermOrigin.USER_INPUT,
                )
            ],
        ),
        "O": PicoBlock(
            block_type="O",
            description="Out",
            terms=[
                OntologyTerm(
                    id="o1",
                    label="Valid",
                    vocab_source="MeSH",
                    code="D2",
                    origin=TermOrigin.USER_INPUT,
                )
            ],
        ),
    }

    return ProtocolDefinition(id="test-proto", title="Test", research_question="Question?", pico_structure=blocks)


def test_protocol_request_exists() -> None:
    """Verify ProtocolRequest dataclass exists and can be instantiated."""
    pr = ProtocolRequest(id="req-1", title="Request Title", research_question="RQ?", pico_structure={})
    assert pr.id == "req-1"
    assert pr.title == "Request Title"


def test_valid_terms() -> None:
    """Test that standard valid terms pass validation."""
    terms = ["Myocardial Infarction", "Standard of Care", "Vitamin C"]
    proto = create_protocol_with_terms(terms)
    # Should not raise
    ProtocolValidator.validate(proto)


def test_invalid_term_and() -> None:
    """Test rejection of ' AND '."""
    terms = ["Heart Attack AND Stroke"]
    proto = create_protocol_with_terms(terms)
    with pytest.raises(ValueError, match="contains ' AND '"):
        ProtocolValidator.validate(proto)


def test_invalid_term_or() -> None:
    """Test rejection of ' OR '."""
    terms = ["Cancer OR Tumor"]
    proto = create_protocol_with_terms(terms)
    with pytest.raises(ValueError, match="contains ' OR '"):
        ProtocolValidator.validate(proto)


def test_invalid_term_not() -> None:
    """Test rejection of 'NOT '."""
    terms = ["NOT Healthy"]
    proto = create_protocol_with_terms(terms)
    with pytest.raises(ValueError, match="contains 'NOT '"):
        ProtocolValidator.validate(proto)


def test_invalid_term_semicolon() -> None:
    """Test rejection of semicolon."""
    terms = ["Term1; Term2"]
    proto = create_protocol_with_terms(terms)
    with pytest.raises(ValueError, match="contains ';'"):
        ProtocolValidator.validate(proto)


def test_invalid_term_comma() -> None:
    """Test rejection of comma."""
    terms = ["Diabetes, Type 2"]
    proto = create_protocol_with_terms(terms)
    with pytest.raises(ValueError, match="contains ','"):
        ProtocolValidator.validate(proto)


def test_valid_term_embedded_and() -> None:
    """Test that 'Standard' (containing 'and' but not ' AND ') is allowed."""
    terms = ["Standard", "Bandage", "Grand"]
    proto = create_protocol_with_terms(terms)
    ProtocolValidator.validate(proto)
