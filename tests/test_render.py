import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


@pytest.fixture
def sample_protocol() -> ProtocolDefinition:
    """Fixture for a populated ProtocolDefinition."""
    return ProtocolDefinition(
        id="proto-123",
        title="Test Protocol",
        research_question="Does Aspirin prevent heart attacks?",
        pico_structure={
            "P": PicoBlock(
                block_type="P",
                description="Patient Population",
                terms=[
                    OntologyTerm(
                        id="t1",
                        label="Adults",
                        vocab_source="MeSH",
                        code="D000328",
                        origin=TermOrigin.USER_INPUT,
                    ),
                    OntologyTerm(
                        id="t2",
                        label="Elderly",
                        vocab_source="MeSH",
                        code="D000368",
                        origin=TermOrigin.SYSTEM_EXPANSION,
                    ),
                ],
            ),
            "I": PicoBlock(
                block_type="I",
                description="Intervention",
                terms=[
                    OntologyTerm(
                        id="t3",
                        label="Aspirin",
                        vocab_source="RxNorm",
                        code="1191",
                        origin=TermOrigin.HUMAN_INJECTION,
                    ),
                    OntologyTerm(
                        id="t4",
                        label="Placebo",
                        vocab_source="MeSH",
                        code="D010919",
                        origin=TermOrigin.SYSTEM_EXPANSION,
                        is_active=False,
                        override_reason="Not interested in placebo comparison",
                    ),
                ],
            ),
        },
        status=ProtocolStatus.DRAFT,
    )


def test_render_html_basic(sample_protocol: ProtocolDefinition) -> None:
    """Test basic HTML rendering of active terms."""
    html_output = sample_protocol.render(format="html")

    # Check for P block
    assert "Patient Population" in html_output

    # Check User Input (Blue, Bold)
    assert '<b style="color: blue">Adults</b>' in html_output

    # Check System Expansion (Grey, Italics)
    assert '<i style="color: grey">Elderly</i>' in html_output


def test_render_html_deleted(sample_protocol: ProtocolDefinition) -> None:
    """Test HTML rendering of deleted terms."""
    html_output = sample_protocol.render(format="html")

    # Check Deleted Term (Red, Strikethrough, Tooltip)
    # The exact HTML structure depends on implementation, but searching for fragments
    assert "Placebo" in html_output
    assert "color: red" in html_output
    assert "text-decoration: line-through" in html_output
    assert 'title="Reason: Not interested in placebo comparison"' in html_output

    # Ensure it preserves the origin tag type (System -> Italics) even if deleted
    # We expect <i ... style="... color: red ...">Placebo</i>
    assert "<i " in html_output
    # Using regex or simpler string check might be needed if attributes are reordered
    # For now, strict substring check if implementation is deterministic


def test_render_human_injection(sample_protocol: ProtocolDefinition) -> None:
    """Test that HUMAN_INJECTION is rendered like USER_INPUT."""
    html_output = sample_protocol.render(format="html")

    # Aspirin is HUMAN_INJECTION -> Should be Blue/Bold
    assert '<b style="color: blue">Aspirin</b>' in html_output


def test_render_html_escaping() -> None:
    """Test that user input is escaped to prevent XSS."""
    proto = ProtocolDefinition(
        id="xss-1",
        title="XSS Test",
        research_question="Safety",
        pico_structure={
            "O": PicoBlock(
                block_type="O",
                description="Outcome",
                terms=[
                    OntologyTerm(
                        id="bad-1",
                        label="<script>alert('XSS')</script>",
                        vocab_source="Hack",
                        code="666",
                        origin=TermOrigin.USER_INPUT,
                    )
                ],
            )
        },
    )

    html_output = proto.render(format="html")

    assert "<script>" not in html_output
    assert (
        "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in html_output
        or "&lt;script&gt;alert('XSS')&lt;/script&gt;" in html_output
    )


def test_render_unsupported_format(sample_protocol: ProtocolDefinition) -> None:
    """Test that unsupported formats raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported format"):
        sample_protocol.render(format="markdown")


def test_render_empty_structure() -> None:
    """Test rendering with no blocks."""
    proto = ProtocolDefinition(
        id="empty-1",
        title="Empty",
        research_question="Empty?",
        pico_structure={},
    )
    html_output = proto.render(format="html")
    assert html_output.strip() == "" or "div" in html_output  # Depending on container
