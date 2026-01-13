import pytest
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


# Helpers
def create_base_protocol() -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-complex",
        title="Complex Test",
        research_question="Complex Q?",
        pico_structure={
            "P": PicoBlock(
                block_type="P",
                description="Population",
                terms=[
                    OntologyTerm(
                        id="term-1",
                        label="Existing Term",
                        vocab_source="MeSH",
                        code="D001",
                        origin=TermOrigin.SYSTEM_EXPANSION,
                        is_active=True,
                    )
                ],
            )
        },
        status=ProtocolStatus.DRAFT,
    )


def test_inject_term_idempotency_content_mismatch() -> None:
    """
    Verify that injecting a term with an existing ID but different content
    does NOT update the existing term. The operation should be silently ignored.
    """
    proto = create_base_protocol()

    # Same ID as term-1, but different label
    different_content_term = OntologyTerm(
        id="term-1",
        label="Completely Different Label",
        vocab_source="MeSH",
        code="D999",
        origin=TermOrigin.USER_INPUT,  # Origin will be forced to HUMAN_INJECTION anyway, but ignored here
    )

    proto.inject_term("P", different_content_term)

    # Check that the term in P is still the original one
    stored_term = proto.pico_structure["P"].terms[0]
    assert stored_term.label == "Existing Term"
    assert stored_term.code == "D001"
    # Origin should arguably remain what it was (SYSTEM_EXPANSION),
    # since we ignored the injection.
    assert stored_term.origin == TermOrigin.SYSTEM_EXPANSION


def test_inject_term_inactive_term_interaction() -> None:
    """
    Verify that injecting a term that exists but is inactive (soft-deleted)
    does NOT reactivate it. It should be treated as existing (idempotent ignore).
    """
    proto = create_base_protocol()

    # Soft-delete the existing term
    proto.override_term("term-1", "Not relevant")
    assert proto.pico_structure["P"].terms[0].is_active is False

    # Try to inject it again
    reinject_term = OntologyTerm(
        id="term-1", label="Existing Term", vocab_source="MeSH", code="D001", origin=TermOrigin.HUMAN_INJECTION
    )

    proto.inject_term("P", reinject_term)

    # It should still be inactive
    assert proto.pico_structure["P"].terms[0].is_active is False
    assert proto.pico_structure["P"].terms[0].override_reason == "Not relevant"


def test_inject_term_cross_block_conflict_inactive() -> None:
    """
    Verify that global uniqueness check applies even if the conflicting term
    in another block is inactive.
    """
    proto = create_base_protocol()

    # Soft-delete term in P
    proto.override_term("term-1", "Remove from P")

    # Try to inject term-1 into I
    conflict_term = OntologyTerm(
        id="term-1", label="Term 1", vocab_source="MeSH", code="D001", origin=TermOrigin.HUMAN_INJECTION
    )

    with pytest.raises(ValueError, match="Term ID 'term-1' already exists in block 'P'"):
        proto.inject_term("I", conflict_term)


def test_inject_term_pending_review_state() -> None:
    """Verify that inject_term works when status is PENDING_REVIEW."""
    proto = create_base_protocol()
    proto.status = ProtocolStatus.PENDING_REVIEW

    new_term = OntologyTerm(
        id="term-new", label="Review Term", vocab_source="MeSH", code="D002", origin=TermOrigin.USER_INPUT
    )

    proto.inject_term("P", new_term)

    assert len(proto.pico_structure["P"].terms) == 2
    assert proto.pico_structure["P"].terms[1].id == "term-new"


def test_inject_term_unicode() -> None:
    """Verify that inject_term handles Unicode characters correctly."""
    proto = create_base_protocol()

    unicode_term = OntologyTerm(
        id="term-µ", label="Müller Cells (Glial)", vocab_source="MeSH", code="D003-µ", origin=TermOrigin.USER_INPUT
    )

    proto.inject_term("O", unicode_term)

    assert "O" in proto.pico_structure
    injected = proto.pico_structure["O"].terms[0]
    assert injected.id == "term-µ"
    assert injected.label == "Müller Cells (Glial)"
