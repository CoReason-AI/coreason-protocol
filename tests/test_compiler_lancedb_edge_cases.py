import json

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
def complex_protocol() -> ProtocolDefinition:
    p_term = OntologyTerm(id="p1", label="Patient", vocab_source="MeSH", code="D000", origin=TermOrigin.USER_INPUT)
    i_term = OntologyTerm(
        id="i1", label="Intervention", vocab_source="MeSH", code="D001", origin=TermOrigin.SYSTEM_EXPANSION
    )

    pico = {
        "P": PicoBlock(block_type="P", description="Pop", terms=[p_term]),
        "I": PicoBlock(block_type="I", description="Int", terms=[i_term]),
    }

    return ProtocolDefinition(
        id="proto-complex",
        title="Complex Protocol",
        research_question="Original Question",
        pico_structure=pico,
        status=ProtocolStatus.DRAFT,
    )


def test_lancedb_ignores_complex_pico(complex_protocol: ProtocolDefinition) -> None:
    """
    Verify that the compiler ignores PICO structure and only uses research_question.
    This ensures that the 'filter' field remains empty as per current requirements,
    regardless of how rich the PICO data is.
    """
    compiler = StrategyCompiler()
    strategy = compiler.compile(complex_protocol, target="LANCEDB")

    data = json.loads(strategy.query_string)

    # Vector should match research question exactly
    assert data["vector"] == "Original Question"

    # Filter should be strictly empty, ignoring the P/I blocks present
    assert data["filter"] == ""

    # Sanity check: ensure the PICO data didn't leak into the vector
    assert "Patient" not in data["vector"]
    assert "D000" not in data["vector"]


def test_lancedb_unicode_and_injection() -> None:
    """
    Test robust JSON handling for:
    1. JSON Injection attempts (quotes, braces)
    2. Unicode/Emoji
    3. Control characters
    """
    # malicious_input attempts to close the JSON string and add a new field
    malicious_input = 'Start ", "filter": "hacked", "ignore": "'
    unicode_input = "End 🦁 🤦‍♂️ \u2603"

    full_question = f"{malicious_input} {unicode_input}"

    proto = ProtocolDefinition(
        id="proto-edge",
        title="Edge Case",
        research_question=full_question,
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, target="LANCEDB")

    data = json.loads(strategy.query_string)

    # The value should contain the literal characters, not interpreted as JSON structure
    assert data["vector"] == full_question
    assert data["filter"] == ""

    # Verify the "hacked" filter was NOT created as a top-level key
    assert len(data.keys()) == 2
    assert "ignore" not in data


def test_lancedb_massive_input() -> None:
    """
    Test handling of a very large research question (10KB).
    Ensures no serialization crashes or truncation.
    """
    large_text = "word " * 2000  # approx 10KB

    proto = ProtocolDefinition(
        id="proto-large",
        title="Large Input",
        research_question=large_text,
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, target="LANCEDB")

    data = json.loads(strategy.query_string)

    assert data["vector"] == large_text
    assert len(data["vector"]) == len(large_text)
    assert data["filter"] == ""
