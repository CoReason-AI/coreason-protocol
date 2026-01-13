from coreason_protocol.types import (
    OntologyTerm,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


def create_empty_protocol() -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-empty",
        title="Empty Protocol",
        research_question="Empty Q?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )


def test_inject_term_duplicate_label_allowed() -> None:
    """
    Verify that injecting a term with a label that already exists (but different ID)
    is allowed. The spec enforces ID uniqueness, not label uniqueness.
    """
    proto = create_empty_protocol()

    # Create block P with one term
    term1 = OntologyTerm(
        id="id-1", label="Heart Attack", vocab_source="MeSH", code="D001", origin=TermOrigin.SYSTEM_EXPANSION
    )
    proto.inject_term("P", term1)

    # Inject second term with SAME label but DIFFERENT ID
    term2 = OntologyTerm(
        id="id-2",
        label="Heart Attack",  # Duplicate label
        vocab_source="ICD-10",
        code="I21",
        origin=TermOrigin.HUMAN_INJECTION,
    )

    proto.inject_term("P", term2)

    assert len(proto.pico_structure["P"].terms) == 2
    assert proto.pico_structure["P"].terms[0].id == "id-1"
    assert proto.pico_structure["P"].terms[1].id == "id-2"


def test_inject_term_s_block() -> None:
    """Verify injection works for the 'S' (Study Design) block."""
    proto = create_empty_protocol()

    term_s = OntologyTerm(
        id="term-s",
        label="Randomized Controlled Trial",
        vocab_source="MeSH",
        code="D01655",
        origin=TermOrigin.HUMAN_INJECTION,
    )

    proto.inject_term("S", term_s)

    assert "S" in proto.pico_structure
    assert proto.pico_structure["S"].block_type == "S"
    assert proto.pico_structure["S"].terms[0].id == "term-s"


def test_inject_multiple_terms() -> None:
    """Verify injecting multiple terms sequentially works correctly."""
    proto = create_empty_protocol()

    for i in range(5):
        term = OntologyTerm(
            id=f"term-{i}", label=f"Label {i}", vocab_source="Test", code=f"C{i}", origin=TermOrigin.USER_INPUT
        )
        proto.inject_term("P", term)

    assert len(proto.pico_structure["P"].terms) == 5
    assert proto.pico_structure["P"].terms[4].id == "term-4"


def test_inject_into_empty_structure() -> None:
    """Verify injection into a protocol with completely empty pico_structure."""
    proto = create_empty_protocol()
    assert not proto.pico_structure

    term = OntologyTerm(id="t1", label="First Term", vocab_source="Src", code="C1", origin=TermOrigin.HUMAN_INJECTION)

    proto.inject_term("P", term)

    assert "P" in proto.pico_structure
    assert len(proto.pico_structure["P"].terms) == 1
