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


def test_compile_graph_basic(basic_protocol: ProtocolDefinition) -> None:
    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="GRAPH")

    assert strategy.target == "GRAPH"
    assert strategy.validation_status == "PRESS_PASSED"

    qs = strategy.query_string
    # Expected components
    # First block (P): MATCH (p:Publication)-[:HAS_MESH]->(t:Term) WHERE t.code IN ['D009203', 'I21']
    # Second block (I): WITH p MATCH (p)-[:HAS_MESH]->(t:Term) WHERE t.code IN ['D001241']
    # End: RETURN p

    expected_part1 = "MATCH (p:Publication)-[:HAS_MESH]->(t:Term) WHERE t.code IN ['D009203', 'I21']"
    expected_part2 = "WITH p MATCH (p)-[:HAS_MESH]->(t:Term) WHERE t.code IN ['D001241']"
    expected_end = "RETURN p"

    assert expected_part1 in qs
    assert expected_part2 in qs
    assert qs.endswith(expected_end)


def test_compile_graph_single_block(basic_protocol: ProtocolDefinition) -> None:
    # Remove I block
    del basic_protocol.pico_structure["I"]

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="GRAPH")

    qs = strategy.query_string
    # Should not have WITH p ...
    assert "WITH p" not in qs
    assert "MATCH (p:Publication)-[:HAS_MESH]->(t:Term) WHERE t.code IN ['D009203', 'I21']" in qs
    assert qs.endswith("RETURN p")


def test_compile_graph_inactive_terms(basic_protocol: ProtocolDefinition) -> None:
    # Set one P term to inactive
    basic_protocol.pico_structure["P"].terms[1].is_active = False  # Myocardial Infarction (I21)

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="GRAPH")

    qs = strategy.query_string
    # Should only contain D009203 in the first list
    assert "['D009203']" in qs
    assert "I21" not in qs


def test_compile_graph_empty_block(basic_protocol: ProtocolDefinition) -> None:
    # Add empty C block
    basic_protocol.pico_structure["C"] = PicoBlock(block_type="C", description="Comparator", terms=[])

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="GRAPH")

    qs = strategy.query_string
    # C block should be ignored
    # Just P and I logic
    assert qs.count("MATCH") == 2  # One for P, one for I
    assert qs.count("WITH p") == 1


def test_compile_graph_no_active_terms(basic_protocol: ProtocolDefinition) -> None:
    # Deactivate all
    for block in basic_protocol.pico_structure.values():
        for term in block.terms:
            term.is_active = False

    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol, target="GRAPH")

    assert strategy.query_string == ""
