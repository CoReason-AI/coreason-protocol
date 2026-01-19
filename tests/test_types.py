from datetime import datetime, timezone

import pytest
from coreason_protocol.types import (
    ApprovalRecord,
    ExecutableStrategy,
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)
from pydantic import ValidationError


def test_ontology_term_defaults() -> None:
    term = OntologyTerm(id="123", label="Test Term", vocab_source="MeSH", code="D123", origin=TermOrigin.USER_INPUT)
    assert term.is_active is True
    assert term.override_reason is None


def test_pico_block_logic_operator_default() -> None:
    block = PicoBlock(block_type="P", description="Population", terms=[])
    assert block.logic_operator == "OR"


def test_protocol_definition_defaults() -> None:
    pd = ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="Does X cause Y?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )
    assert pd.execution_strategies == []
    assert pd.approval_history is None


def test_protocol_definition_methods_exist() -> None:
    pd = ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="Does X cause Y?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )
    # render() is tested in test_rendering.py, just ensure it returns a string
    assert isinstance(pd.render(), str)
    # lock() is tested in test_locking.py


def test_full_instantiation() -> None:
    term = OntologyTerm(
        id="term-1", label="Aspirin", vocab_source="RxNorm", code="1191", origin=TermOrigin.SYSTEM_EXPANSION
    )
    block = PicoBlock(block_type="I", description="Intervention", terms=[term])
    approval = ApprovalRecord(approver_id="admin", timestamp=datetime.now(timezone.utc), veritas_hash="hash123")
    strategy = ExecutableStrategy(target="PUBMED", query_string="Aspirin", validation_status="PRESS_PASSED")

    pd = ProtocolDefinition(
        id="proto-full",
        title="Full Protocol",
        research_question="Q?",
        pico_structure={"I": block},
        execution_strategies=[strategy],
        status=ProtocolStatus.APPROVED,
        approval_history=approval,
    )

    assert pd.id == "proto-full"
    assert pd.pico_structure["I"].terms[0].label == "Aspirin"
    assert pd.status == ProtocolStatus.APPROVED
    assert pd.approval_history is not None
    assert pd.approval_history.veritas_hash == "hash123"


# --- Complex / Edge Case Tests ---


def test_pico_structure_validation_mismatch() -> None:
    """Test that validation fails if dictionary key doesn't match block_type."""
    block = PicoBlock(block_type="I", description="Intervention", terms=[])

    with pytest.raises(ValidationError) as excinfo:
        ProtocolDefinition(
            id="proto-bad",
            title="Bad Proto",
            research_question="Q?",
            pico_structure={"P": block},  # Key "P" mismatch with block_type "I"
            status=ProtocolStatus.DRAFT,
        )
    assert "Key mismatch in pico_structure" in str(excinfo.value)


def test_unicode_handling() -> None:
    """Test handling of Unicode characters in labels and descriptions."""
    unicode_str = "München ❤️ 🍺"
    term = OntologyTerm(id="u-1", label=unicode_str, vocab_source="Uni", code="U1", origin=TermOrigin.USER_INPUT)
    block = PicoBlock(block_type="P", description=unicode_str, terms=[term])
    pd = ProtocolDefinition(
        id="proto-uni",
        title=unicode_str,
        research_question=unicode_str,
        pico_structure={"P": block},
        status=ProtocolStatus.DRAFT,
    )
    assert pd.title == unicode_str
    assert pd.pico_structure["P"].description == unicode_str
    assert pd.pico_structure["P"].terms[0].label == unicode_str


def test_timezone_aware_timestamp() -> None:
    """Ensure timestamps are handled correctly (timezone awareness)."""
    now_utc = datetime.now(timezone.utc)
    approval = ApprovalRecord(approver_id="admin", timestamp=now_utc, veritas_hash="abc")
    # Pydantic should preserve the timezone info
    assert approval.timestamp.tzinfo == timezone.utc


def test_large_number_of_terms() -> None:
    """Test performance/correctness with a larger list of terms."""
    terms = [
        OntologyTerm(
            id=f"t-{i}", label=f"Term {i}", vocab_source="Test", code=f"C{i}", origin=TermOrigin.SYSTEM_EXPANSION
        )
        for i in range(1000)
    ]
    block = PicoBlock(block_type="P", description="Big Population", terms=terms)
    pd = ProtocolDefinition(
        id="proto-big",
        title="Big Proto",
        research_question="Q?",
        pico_structure={"P": block},
        status=ProtocolStatus.DRAFT,
    )
    assert len(pd.pico_structure["P"].terms) == 1000
    assert pd.pico_structure["P"].terms[999].code == "C999"


def test_term_origin_enum_enforcement() -> None:
    """Ensure invalid TermOrigin values are rejected."""
    with pytest.raises(ValidationError):
        OntologyTerm(id="123", label="Bad Origin", vocab_source="MeSH", code="D123", origin="INVALID_ORIGIN")


def test_execution_strategies_default() -> None:
    """Ensure execution_strategies defaults to empty list and accepts valid strategies."""
    pd = ProtocolDefinition(
        id="proto-strat", title="Strat Proto", research_question="Q?", pico_structure={}, status=ProtocolStatus.DRAFT
    )
    assert pd.execution_strategies == []

    # Now with strategies
    strategy = ExecutableStrategy(target="A", query_string="B", validation_status="C")
    pd2 = ProtocolDefinition(
        id="proto-strat-2",
        title="Strat Proto 2",
        research_question="Q?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
        execution_strategies=[strategy],
    )
    assert len(pd2.execution_strategies) == 1
