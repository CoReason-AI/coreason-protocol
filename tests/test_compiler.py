import pytest
from coreason_identity.models import UserContext

from coreason_protocol.compiler import StrategyCompiler
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


@pytest.fixture
def mock_context() -> UserContext:
    return UserContext(
        user_id="test-user",
        email="test@coreason.ai",
        groups=["researcher"],
        scopes=["*"],
        claims={},
    )


@pytest.fixture
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


def test_compile_pubmed_basic(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, context=mock_context, target="PUBMED")

    assert strategy.target == "PUBMED"
    assert strategy.validation_status == "PRESS_PASSED"

    qs = strategy.query_string
    assert '"Heart Attack"[Mesh]' in qs
    assert '"Myocardial Infarction"[TiAb]' in qs
    assert '"Aspirin"[Mesh]' in qs
    assert " OR " in qs
    assert " AND " in qs

    assert qs == '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])'


def test_compile_pubmed_inactive_terms(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    # Set one P term to inactive
    basic_protocol.pico_structure["P"].terms[1].is_active = False  # Myocardial Infarction
    basic_protocol.pico_structure["P"].terms[1].override_reason = "Removed"

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, context=mock_context, target="PUBMED")

    qs = strategy.query_string
    assert '"Myocardial Infarction"[TiAb]' not in qs
    assert '"Heart Attack"[Mesh]' in qs

    assert qs == '("Heart Attack"[Mesh] AND "Aspirin"[Mesh])'


def test_compile_pubmed_empty_block(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    # Add empty C block
    basic_protocol.pico_structure["C"] = PicoBlock(block_type="C", description="Comparator", terms=[])

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, context=mock_context, target="PUBMED")

    # Should ignore C block
    qs = strategy.query_string
    assert '"Heart Attack"[Mesh]' in qs
    assert '"Aspirin"[Mesh]' in qs
    assert qs == '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])'


def test_compile_pubmed_unsupported_target(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    compiler = StrategyCompiler()
    with pytest.raises(ValueError, match="Unsupported target"):
        compiler.compile(basic_protocol, context=mock_context, target="INVALID_TARGET")


def test_protocol_convenience_method(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    strategies = basic_protocol.compile(context=mock_context, target="PUBMED")
    assert len(strategies) == 1
    assert strategies[0].target == "PUBMED"
    assert strategies[0].query_string == '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND "Aspirin"[Mesh])'

    # Check it was stored
    assert len(basic_protocol.execution_strategies) == 1
    assert basic_protocol.execution_strategies[0] == strategies[0]


def test_compile_complex_structure(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    i_term2 = OntologyTerm(
        id="i2", label="Clopidogrel", vocab_source="MeSH", code="D0000", origin=TermOrigin.SYSTEM_EXPANSION
    )

    basic_protocol.pico_structure["I"].terms.append(i_term2)
    basic_protocol.pico_structure["I"].logic_operator = "AND"

    c_term = OntologyTerm(id="c1", label="Placebo", vocab_source="MeSH", code="D010919", origin=TermOrigin.USER_INPUT)
    basic_protocol.pico_structure["C"] = PicoBlock(block_type="C", description="Comp", terms=[c_term])

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, context=mock_context)
    qs = strategy.query_string

    expected = (
        '(("Heart Attack"[Mesh] OR "Myocardial Infarction"[TiAb]) AND '
        '("Aspirin"[Mesh] AND "Clopidogrel"[Mesh]) AND "Placebo"[Mesh])'
    )
    assert qs == expected


def test_compile_no_active_terms(basic_protocol: ProtocolDefinition, mock_context: UserContext) -> None:
    # Deactivate all terms
    for block in basic_protocol.pico_structure.values():
        for term in block.terms:
            term.is_active = False
            term.override_reason = "Testing"

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, context=mock_context)
    assert strategy.query_string == ""


def test_compile_not_operator(mock_context: UserContext) -> None:
    p_term1 = OntologyTerm(id="p1", label="A", vocab_source="MeSH", code="1", origin=TermOrigin.USER_INPUT)
    p_term2 = OntologyTerm(id="p2", label="B", vocab_source="MeSH", code="2", origin=TermOrigin.USER_INPUT)

    pico = {"P": PicoBlock(block_type="P", description="P", terms=[p_term1, p_term2], logic_operator="NOT")}

    proto = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure=pico)

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, context=mock_context)
    qs = strategy.query_string

    assert qs == '((NOT "A"[Mesh]) AND (NOT "B"[Mesh]))'
