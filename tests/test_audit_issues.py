from coreason_identity.models import UserContext
from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


def test_compile_idempotency(test_context: UserContext) -> None:
    # Setup basic protocol
    p_term = OntologyTerm(
        id="p1",
        label="Heart Attack",
        vocab_source="MeSH",
        code="D009203",
        origin=TermOrigin.USER_INPUT,
    )
    pico = {
        "P": PicoBlock(
            block_type="P",
            description="Patient",
            terms=[p_term],
            logic_operator="OR",
        )
    }
    proto = ProtocolDefinition(
        id="proto-idempotency",
        title="Test Protocol",
        research_question="Q",
        pico_structure=pico,
        status=ProtocolStatus.DRAFT,
    )

    # First compile
    proto.compile(context=test_context, target="PUBMED")
    assert len(proto.execution_strategies) == 1
    assert proto.execution_strategies[0].target == "PUBMED"

    # Second compile
    proto.compile(context=test_context, target="PUBMED")

    # Audit Expectation: Should still be 1, updated.
    # Current behavior likely appends (so 2), which we want to fix.
    assert len(proto.execution_strategies) == 1
    assert proto.execution_strategies[0].target == "PUBMED"
