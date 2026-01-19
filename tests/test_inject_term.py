import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


# Mock Data
def create_sample_protocol() -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-123",
        title="Test Protocol",
        research_question="Does X cause Y?",
        pico_structure={
            "P": PicoBlock(
                block_type="P",
                description="Population",
                terms=[
                    OntologyTerm(
                        id="term-1",
                        label="Humans",
                        vocab_source="MeSH",
                        code="D123",
                        origin=TermOrigin.SYSTEM_EXPANSION,
                    )
                ],
            )
        },
        status=ProtocolStatus.DRAFT,
    )


def create_sample_term(term_id: str = "term-2") -> OntologyTerm:
    return OntologyTerm(
        id=term_id,
        label="New Term",
        vocab_source="MeSH",
        code="D456",
        origin=TermOrigin.USER_INPUT,  # Deliberately wrong to test enforcement
    )


def test_inject_term_success_existing_block() -> None:
    """Test injecting a term into an existing block."""
    proto = create_sample_protocol()
    new_term = create_sample_term("term-2")

    proto.inject_term("P", new_term)

    assert len(proto.pico_structure["P"].terms) == 2
    injected = proto.pico_structure["P"].terms[1]
    assert injected.id == "term-2"
    assert injected.origin == TermOrigin.HUMAN_INJECTION  # Must be enforced


def test_inject_term_success_new_block() -> None:
    """Test injecting a term into a non-existent block creates the block."""
    proto = create_sample_protocol()
    new_term = create_sample_term("term-3")

    proto.inject_term("I", new_term)

    assert "I" in proto.pico_structure
    block = proto.pico_structure["I"]
    assert block.block_type == "I"
    assert block.description == "I"  # Default description? Or should we handle this?
    # The spec didn't specify description for auto-created blocks.
    # Let's assume description defaults to the block type or generic text for now,
    # and update if needed. But wait, PicoBlock description is mandatory and checks non-empty.
    # I will have to decide on a default description. "Manual Injection Block" or similar.
    assert len(block.terms) == 1
    assert block.terms[0].id == "term-3"


def test_inject_term_idempotency() -> None:
    """Test that injecting an existing term ID into the same block is ignored."""
    proto = create_sample_protocol()

    # Try to inject term-1 again into P
    duplicate_term = OntologyTerm(
        id="term-1",  # Same ID
        label="Different Label",
        vocab_source="MeSH",
        code="D123",
        origin=TermOrigin.USER_INPUT,
    )

    proto.inject_term("P", duplicate_term)

    # Should still be 1 term
    assert len(proto.pico_structure["P"].terms) == 1
    # Should not have updated the label
    assert proto.pico_structure["P"].terms[0].label == "Humans"


def test_inject_term_global_uniqueness_error() -> None:
    """Test that injecting a term ID that exists in a DIFFERENT block raises ValueError."""
    proto = create_sample_protocol()
    # P block has term-1

    # Create I block
    proto.inject_term("I", create_sample_term("term-2"))

    # Try to inject term-1 into I block
    conflict_term = create_sample_term("term-1")

    with pytest.raises(ValueError, match="Term ID 'term-1' already exists"):
        proto.inject_term("I", conflict_term)


def test_inject_term_wrong_state() -> None:
    """Test that injection fails if status is not DRAFT or PENDING_REVIEW."""
    proto = create_sample_protocol()
    proto.status = ProtocolStatus.APPROVED
    new_term = create_sample_term("term-99")

    with pytest.raises(RuntimeError, match="Cannot modify protocol"):
        proto.inject_term("P", new_term)


def test_inject_term_invalid_block_type() -> None:
    """Test that injection fails if block_type is invalid (managed by PicoBlock validation)."""
    proto = create_sample_protocol()
    new_term = create_sample_term("term-100")

    # "Z" is not a valid PicoBlock type (P, I, C, O, S)
    # This might fail when creating the PicoBlock
    with pytest.raises(ValueError, match="block_type must be one of"):
        proto.inject_term("Z", new_term)
