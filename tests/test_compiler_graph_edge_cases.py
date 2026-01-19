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
def basic_proto_with_quotes() -> ProtocolDefinition:
    term = OntologyTerm(
        id="t1",
        label="Test",
        vocab_source="MeSH",
        code="O'Neil",  # Contains single quote
        origin=TermOrigin.USER_INPUT,
    )
    pico = {"P": PicoBlock(block_type="P", description="Pop", terms=[term])}
    return ProtocolDefinition(
        id="p1", title="T", research_question="Q", pico_structure=pico, status=ProtocolStatus.DRAFT
    )


def test_compile_graph_injection_prevention(basic_proto_with_quotes: ProtocolDefinition) -> None:
    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_proto_with_quotes, target="GRAPH")

    qs = strategy.query_string
    # Should contain escaped quote: 'O\'Neil'
    # Note: in Python string literal, backslash needs escaping if raw string not used, but let's check content.
    # The output string should be ... code IN ['O\'Neil'] ...
    assert "\\'Neil" in qs
    assert "['O\\'Neil']" in qs


def test_compile_graph_full_pico_structure() -> None:
    # Construct full P, I, C, O, S
    terms = [
        OntologyTerm(id=f"t{i}", label=f"L{i}", vocab_source="S", code=f"C{i}", origin=TermOrigin.USER_INPUT)
        for i in range(5)
    ]
    pico = {
        "P": PicoBlock(block_type="P", description="P", terms=[terms[0]]),
        "I": PicoBlock(block_type="I", description="I", terms=[terms[1]]),
        "C": PicoBlock(block_type="C", description="C", terms=[terms[2]]),
        "O": PicoBlock(block_type="O", description="O", terms=[terms[3]]),
        "S": PicoBlock(block_type="S", description="S", terms=[terms[4]]),
    }
    proto = ProtocolDefinition(
        id="full", title="Full", research_question="Q", pico_structure=pico, status=ProtocolStatus.DRAFT
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, target="GRAPH")
    qs = strategy.query_string

    # Logic:
    # 1. MATCH (p)... WHERE code IN ['C0']
    # 2. WITH p MATCH ... WHERE code IN ['C1']
    # 3. WITH p MATCH ... WHERE code IN ['C2']
    # 4. WITH p MATCH ... WHERE code IN ['C3']
    # 5. WITH p MATCH ... WHERE code IN ['C4']
    # 6. RETURN p

    matches = qs.count("MATCH")
    assert matches == 5
    withs = qs.count("WITH p")
    assert withs == 4
    assert qs.endswith("RETURN p")

    # Verify order
    parts = qs.split("WITH p")
    assert "C0" in parts[0]
    assert "C1" in parts[1]
    assert "C2" in parts[2]
    assert "C3" in parts[3]
    assert "C4" in parts[4]


def test_compile_graph_start_with_later_blocks() -> None:
    # Only C and O blocks
    terms = [
        OntologyTerm(id=f"t{i}", label=f"L{i}", vocab_source="S", code=f"C{i}", origin=TermOrigin.USER_INPUT)
        for i in range(2)
    ]
    pico = {
        "C": PicoBlock(block_type="C", description="C", terms=[terms[0]]),
        "O": PicoBlock(block_type="O", description="O", terms=[terms[1]]),
    }
    proto = ProtocolDefinition(
        id="partial", title="Partial", research_question="Q", pico_structure=pico, status=ProtocolStatus.DRAFT
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, target="GRAPH")
    qs = strategy.query_string

    # Should start with MATCH for C (C0), then WITH p MATCH for O (C1)
    assert qs.startswith("MATCH")
    assert "C0" in qs.split("WITH p")[0]
    assert "C1" in qs.split("WITH p")[1]
    assert qs.count("MATCH") == 2
    assert qs.count("WITH p") == 1


def test_compile_graph_unicode_codes() -> None:
    term = OntologyTerm(id="t1", label="L", vocab_source="S", code="München", origin=TermOrigin.USER_INPUT)
    pico = {"P": PicoBlock(block_type="P", description="P", terms=[term])}
    proto = ProtocolDefinition(
        id="uni", title="U", research_question="Q", pico_structure=pico, status=ProtocolStatus.DRAFT
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, target="GRAPH")
    qs = strategy.query_string

    assert "['München']" in qs
