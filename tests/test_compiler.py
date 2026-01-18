import pytest

from coreason_protocol.compiler import StrategyCompiler
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


@pytest.fixture  # type: ignore[misc]
def basic_protocol() -> ProtocolDefinition:
    p_term1 = OntologyTerm(
        id="p1",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )
    p_term2 = OntologyTerm(
        id="p2",
        label="Myocardial Infarction",
        vocab_source="ICD-10",
        code="I21",
        origin=TermOrigin.SYSTEM_EXPANSION,
    )

    i_term1 = OntologyTerm(
        id="i1",
        label="Aspirin",
        vocab_source="MeSH",
        code="D001241",
        origin=TermOrigin.USER_INPUT,
    )

    pico = {
        "P": PicoBlock(
            block_type="P",
            description="Patient",
            terms=[p_term1, p_term2],
            logic_operator="OR",
        ),
        "I": PicoBlock(
            block_type="I",
            description="Intervention",
            terms=[i_term1],
            logic_operator="OR",
        ),
    }

    return ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="Does Aspirin help Heart Attack?",
        pico_structure=pico,
        status=ProtocolStatus.DRAFT,
    )


def test_compile_pubmed_basic(basic_protocol: ProtocolDefinition) -> None:
    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="PUBMED")

    assert strategy.target == "PUBMED"
    assert strategy.validation_status == "PRESS_PASSED"

    # Expected: (("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])
    # Note: Logic ordering of terms within OR might vary depending on implementation stability?
    # boolean.py generally preserves insertion order or sorts.
    # Let's check for components if exact string match is flaky.
    # But for now, we expect deterministic output from our traversal.

    qs = strategy.query_string
    assert '"Heart Attack"[Mesh]' in qs
    assert '"Myocardial Infarction"[TiAb]' in qs
    assert '"Aspirin"[Mesh]' in qs
    assert " OR " in qs
    assert " AND " in qs

    # Check structure
    # (P) AND (I)
    # P = (T1 OR T2)
    # I = T3
    # Result: ((T1 OR T2) AND T3)
    # Or (T1 OR T2) AND T3 depending on paren implementation

    # My implementation wraps every OR/AND in parens
    # ((T1 OR T2) AND T3)
    # Actually, boolean.py might simplify single term OR?
    # My code: if len(terms) == 1: block_expr = term_symbols[0]
    # So I block is just T3.
    # Result: (P_expr AND I_expr)
    # P_expr: (T1 OR T2)
    # I_expr: T3
    # Result: ((T1 OR T2) AND T3)

    assert qs == '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])'


def test_compile_pubmed_inactive_terms(basic_protocol: ProtocolDefinition) -> None:
    # Set one P term to inactive
    basic_protocol.pico_structure["P"].terms[1].is_active = False  # Myocardial Infarction
    basic_protocol.pico_structure["P"].terms[1].override_reason = "Removed"

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="PUBMED")

    qs = strategy.query_string
    assert '"Myocardial Infarction"[TiAb]' not in qs
    assert '"Heart Attack"[Mesh]' in qs

    # P block now has 1 active term. I block has 1 active term.
    # Result: ("Heart Attack"[Mesh] AND "Aspirin"[Mesh])

    assert qs == '("Heart Attack"[Mesh] AND "Aspirin"[Mesh])'


def test_compile_pubmed_empty_block(basic_protocol: ProtocolDefinition) -> None:
    # Add empty C block
    basic_protocol.pico_structure["C"] = PicoBlock(block_type="C", description="Comparator", terms=[])

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="PUBMED")

    # Should ignore C block
    qs = strategy.query_string
    assert '"Heart Attack"[Mesh]' in qs
    assert '"Aspirin"[Mesh]' in qs
    assert qs == '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])'


def test_compile_pubmed_unsupported_target(basic_protocol: ProtocolDefinition) -> None:
    compiler = StrategyCompiler()
    with pytest.raises(ValueError, match="Unsupported target"):
        compiler.compile(basic_protocol, target="LANCEDB")


def test_protocol_convenience_method(basic_protocol: ProtocolDefinition) -> None:
    strategies = basic_protocol.compile(target="PUBMED")
    assert len(strategies) == 1
    assert strategies[0].target == "PUBMED"
    assert strategies[0].query_string == '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])'

    # Check it was stored
    assert len(basic_protocol.execution_strategies) == 1
    assert basic_protocol.execution_strategies[0] == strategies[0]


def test_compile_complex_structure(basic_protocol: ProtocolDefinition) -> None:
    # P: 2 terms (OR)
    # I: 2 terms (AND) -- Assuming we change operator
    # C: 1 term

    i_term2 = OntologyTerm(
        id="i2", label="Clopidogrel", vocab_source="MeSH", code="D0000", origin=TermOrigin.SYSTEM_EXPANSION
    )

    basic_protocol.pico_structure["I"].terms.append(i_term2)
    basic_protocol.pico_structure["I"].logic_operator = "AND"

    c_term = OntologyTerm(id="c1", label="Placebo", vocab_source="MeSH", code="D010919", origin=TermOrigin.USER_INPUT)
    basic_protocol.pico_structure["C"] = PicoBlock(block_type="C", description="Comp", terms=[c_term])

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol)
    qs = strategy.query_string

    # P: (T1 OR T2)
    # I: (T3 AND T4)
    # C: T5
    # Result: ((P) AND (I) AND (C))
    # ((T1 OR T2) AND (T3 AND T4) AND T5)

    expected = (
        '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND '
        '("Aspirin"[Mesh] AND "Clopidogrel"[Mesh]) AND "Placebo"[Mesh])'
    )
    assert qs == expected


def test_compile_no_active_terms(basic_protocol: ProtocolDefinition) -> None:
    # Deactivate all terms
    for block in basic_protocol.pico_structure.values():
        for term in block.terms:
            term.is_active = False
            term.override_reason = "Testing"

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol)
    assert strategy.query_string == ""


def test_compile_not_operator() -> None:
    # Although rare, test NOT operator handling if we implemented it
    # P: NOT (A OR B) -> translated as (NOT A AND NOT B) in my impl

    p_term1 = OntologyTerm(id="p1", label="A", vocab_source="MeSH", code="1", origin=TermOrigin.USER_INPUT)
    p_term2 = OntologyTerm(id="p2", label="B", vocab_source="MeSH", code="2", origin=TermOrigin.USER_INPUT)

    pico = {"P": PicoBlock(block_type="P", description="P", terms=[p_term1, p_term2], logic_operator="NOT")}

    proto = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure=pico)

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto)
    qs = strategy.query_string

    # Expected: ((NOT "A"[Mesh]) AND (NOT "B"[Mesh])) if using NOT as AND NOT logic
    # My impl: not_terms = [NOT(t) for t in terms], AND(*not_terms)
    # Output: ((NOT "A"[Mesh]) AND (NOT "B"[Mesh]))

    assert qs == '((NOT "A"[Mesh]) AND (NOT "B"[Mesh]))'
