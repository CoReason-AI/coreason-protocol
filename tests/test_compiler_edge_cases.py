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
def empty_protocol() -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-edge",
        title="Edge Case Protocol",
        research_question="Edge cases?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )


def test_compile_quotes_in_labels(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    # Term with double quotes
    term = OntologyTerm(
        id="t1", label='Vitamin "D" Supplement', vocab_source="Other", code="X", origin=TermOrigin.USER_INPUT
    )
    empty_protocol.pico_structure["I"] = PicoBlock(block_type="I", description="Intervention", terms=[term])

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    # We expect the internal double quotes to be sanitized to avoid syntax errors
    # E.g., replaced by single quotes
    # "Vitamin 'D' Supplement"[TiAb]
    assert "Vitamin 'D' Supplement" in strategy.query_string
    assert '"Vitamin "D" Supplement"' not in strategy.query_string


def test_compile_boolean_keywords_in_labels(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    # Term containing AND/OR
    term = OntologyTerm(
        id="t1", label="Signs AND Symptoms", vocab_source="MeSH", code="X", origin=TermOrigin.USER_INPUT
    )
    empty_protocol.pico_structure["O"] = PicoBlock(block_type="O", description="Outcome", terms=[term])

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    # Should be wrapped in quotes so AND is literal
    assert '"Signs AND Symptoms"[Mesh]' in strategy.query_string


def test_compile_whitespace_trimming(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    term = OntologyTerm(id="t1", label="  Heart Attack  ", vocab_source="MeSH", code="X", origin=TermOrigin.USER_INPUT)
    empty_protocol.pico_structure["P"] = PicoBlock(block_type="P", description="Patient", terms=[term])

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    assert '"Heart Attack"[Mesh]' in strategy.query_string
    assert "  Heart Attack  " not in strategy.query_string


def test_compile_block_ordering(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    # Insert O then P then I
    t_o = OntologyTerm(id="o1", label="Death", vocab_source="Other", code="O", origin=TermOrigin.USER_INPUT)
    t_p = OntologyTerm(id="p1", label="Patient", vocab_source="Other", code="P", origin=TermOrigin.USER_INPUT)
    t_i = OntologyTerm(id="i1", label="Drug", vocab_source="Other", code="I", origin=TermOrigin.USER_INPUT)

    empty_protocol.pico_structure["O"] = PicoBlock(block_type="O", description="O", terms=[t_o])
    empty_protocol.pico_structure["P"] = PicoBlock(block_type="P", description="P", terms=[t_p])
    empty_protocol.pico_structure["I"] = PicoBlock(block_type="I", description="I", terms=[t_i])

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    # Expected order: P AND I AND O
    # (("Patient"[TiAb]) AND ("Drug"[TiAb]) AND ("Death"[TiAb]))
    # Since we can't easily rely on regex for order in a long string without strict structure assumptions,
    # let's verify the string structure.

    # Assuming the compiler iterates P, I, C, O, S
    # Update: Single-term blocks are not wrapped in extra parentheses by boolean.py/our renderer logic
    assert strategy.query_string == '("Patient"[TiAb] AND "Drug"[TiAb] AND "Death"[TiAb])'


def test_compile_missing_intermediate_blocks(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    # P and O only
    t_p = OntologyTerm(id="p1", label="Patient", vocab_source="Other", code="P", origin=TermOrigin.USER_INPUT)
    t_o = OntologyTerm(id="o1", label="Outcome", vocab_source="Other", code="O", origin=TermOrigin.USER_INPUT)

    empty_protocol.pico_structure["P"] = PicoBlock(block_type="P", description="P", terms=[t_p])
    empty_protocol.pico_structure["O"] = PicoBlock(block_type="O", description="O", terms=[t_o])

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    # Update: Single-term blocks are not wrapped in extra parentheses
    assert strategy.query_string == '("Patient"[TiAb] AND "Outcome"[TiAb])'


def test_compile_unicode_terms(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    term = OntologyTerm(id="t1", label="β-Amyloid", vocab_source="Other", code="X", origin=TermOrigin.USER_INPUT)
    empty_protocol.pico_structure["P"] = PicoBlock(block_type="P", description="P", terms=[term])

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    assert '"β-Amyloid"[TiAb]' in strategy.query_string


def test_compile_many_terms(empty_protocol: ProtocolDefinition, test_context: UserContext) -> None:
    # Add 50 terms to P block
    terms = []
    for i in range(50):
        terms.append(
            OntologyTerm(
                id=f"t{i}", label=f"Term {i}", vocab_source="MeSH", code=str(i), origin=TermOrigin.SYSTEM_EXPANSION
            )
        )

    empty_protocol.pico_structure["P"] = PicoBlock(block_type="P", description="Large Block", terms=terms)

    compiler = StrategyCompiler()
    strategy = compiler.compile(empty_protocol, context=test_context)

    qs = strategy.query_string
    assert qs.count(" OR ") == 49
    assert '"Term 0"[Mesh]' in qs
    assert '"Term 49"[Mesh]' in qs
    # It should be a valid string
    assert qs.startswith("(") and qs.endswith(")")
