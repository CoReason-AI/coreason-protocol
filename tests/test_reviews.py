import pytest

from coreason_protocol.types import OntologyTerm, PicoBlock, ProtocolDefinition, ProtocolStatus, TermOrigin


def test_override_term_success() -> None:
    term = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.SYSTEM_EXPANSION)
    block = PicoBlock(block_type="P", description="Pop", terms=[term])
    pd = ProtocolDefinition(
        id="1", title="T", research_question="Q", pico_structure={"P": block}, status=ProtocolStatus.DRAFT
    )

    # Updated call signature
    pd.override_term("1", "Bad term")

    assert pd.pico_structure["P"].terms[0].is_active is False
    assert pd.pico_structure["P"].terms[0].override_reason == "Bad term"


def test_override_term_fail_status() -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.APPROVED)
    with pytest.raises(RuntimeError, match="Cannot modify protocol in APPROVED state"):
        pd.override_term("1", "R")


def test_override_term_fail_empty_reason() -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.DRAFT)
    with pytest.raises(ValueError, match="Override reason cannot be empty"):
        pd.override_term("1", "   ")  # Whitespace


def test_override_term_fail_missing_block_or_term() -> None:
    term = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.SYSTEM_EXPANSION)
    block = PicoBlock(block_type="P", description="Pop", terms=[term])
    pd = ProtocolDefinition(
        id="1", title="T", research_question="Q", pico_structure={"P": block}, status=ProtocolStatus.DRAFT
    )

    with pytest.raises(ValueError, match="Term ID '999' not found in protocol"):
        pd.override_term("999", "R")


def test_inject_term_success() -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.DRAFT)

    new_term = OntologyTerm(id="inj-1", label="New", vocab_source="Man", code="N", origin=TermOrigin.USER_INPUT)

    # Inject into "I" (will create block)
    pd.inject_term("I", new_term)

    assert "I" in pd.pico_structure
    assert len(pd.pico_structure["I"].terms) == 1
    assert pd.pico_structure["I"].terms[0].id == "inj-1"
    assert pd.pico_structure["I"].terms[0].origin == TermOrigin.HUMAN_INJECTION  # Forced origin


def test_inject_term_idempotency() -> None:
    """If injecting same term ID into same block, should silently succeed."""
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.DRAFT)
    t1 = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.HUMAN_INJECTION)

    pd.inject_term("P", t1)

    # Inject again
    t2 = OntologyTerm(id="1", label="T2", vocab_source="S", code="C", origin=TermOrigin.HUMAN_INJECTION)
    pd.inject_term("P", t2)  # Should be ignored

    assert len(pd.pico_structure["P"].terms) == 1
    # Label should NOT change (first one wins)
    assert pd.pico_structure["P"].terms[0].label == "T"


def test_inject_term_fail_duplicate_global() -> None:
    """Term ID must be globally unique across blocks."""
    t1 = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.SYSTEM_EXPANSION)
    block_p = PicoBlock(block_type="P", description="Pop", terms=[t1])

    pd = ProtocolDefinition(
        id="1", title="T", research_question="Q", pico_structure={"P": block_p}, status=ProtocolStatus.DRAFT
    )

    t_dup = OntologyTerm(id="1", label="Dup", vocab_source="S", code="C", origin=TermOrigin.HUMAN_INJECTION)

    with pytest.raises(ValueError, match="Term ID '1' already exists in block 'P'"):
        pd.inject_term("I", t_dup)  # Try to inject "1" into "I"


def test_inject_term_fail_status() -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.APPROVED)
    t = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.HUMAN_INJECTION)

    with pytest.raises(RuntimeError, match="Cannot modify protocol in APPROVED state"):
        pd.inject_term("P", t)


def test_inject_term_fail_executed() -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.EXECUTED)
    t = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.HUMAN_INJECTION)

    with pytest.raises(RuntimeError, match="Cannot modify protocol in EXECUTED state"):
        pd.inject_term("P", t)
