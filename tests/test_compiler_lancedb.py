import json

import pytest
from coreason_identity.models import UserContext

from coreason_protocol.compiler import StrategyCompiler
from coreason_protocol.types import ProtocolDefinition, ProtocolStatus


@pytest.fixture  # type: ignore[misc]
def basic_protocol_lancedb() -> ProtocolDefinition:
    return ProtocolDefinition(
        id="proto-lance",
        title="LanceDB Test Protocol",
        research_question="Does Vitamin D affect Depression?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )


def test_compile_lancedb_basic(basic_protocol_lancedb: ProtocolDefinition, test_context: UserContext) -> None:
    compiler = StrategyCompiler()
    strategy = compiler.compile(basic_protocol_lancedb, context=test_context, target="LANCEDB")

    assert strategy.target == "LANCEDB"
    assert strategy.validation_status == "PRESS_PASSED"

    # Verify JSON content
    data = json.loads(strategy.query_string)
    assert data["vector"] == "Does Vitamin D affect Depression?"
    assert data["filter"] == ""


def test_compile_lancedb_special_chars(test_context: UserContext) -> None:
    # Test with characters that need JSON escaping
    rq = 'Search "query" with \n newlines and \\ backslashes.'
    proto = ProtocolDefinition(
        id="proto-special",
        title="Special Chars",
        research_question=rq,
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, context=test_context, target="LANCEDB")

    data = json.loads(strategy.query_string)
    assert data["vector"] == rq
    assert data["filter"] == ""


def test_compile_lancedb_empty_rq(test_context: UserContext) -> None:
    proto = ProtocolDefinition(
        id="proto-empty",
        title="Empty RQ",
        research_question="",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )

    compiler = StrategyCompiler()
    strategy = compiler.compile(proto, context=test_context, target="LANCEDB")

    data = json.loads(strategy.query_string)
    assert data["vector"] == ""
