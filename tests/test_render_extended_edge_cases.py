import html

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    TermOrigin,
)


def test_render_inactive_no_reason() -> None:
    """
    Verify that an inactive term without an override reason
    renders with the correct style (Red/Strikethrough) but does NOT
    have a 'title' attribute (tooltip).
    """
    term = OntologyTerm(
        id="t1",
        label="Quiet Deletion",
        vocab_source="MeSH",
        code="D000",
        origin=TermOrigin.SYSTEM_EXPANSION,
        is_active=False,
        override_reason=None,
    )
    block = PicoBlock(block_type="P", description="Pop", terms=[term])

    protocol = ProtocolDefinition(
        id="proto-1",
        title="Test",
        research_question="?",
        pico_structure={"P": block},
    )

    output = protocol.render(format="html")

    # Check style
    assert "color: red" in output
    assert "text-decoration: line-through" in output
    assert "Quiet Deletion" in output

    # Check ABSENCE of title attribute for this term
    # We look for the specific substring that would be generated if reason existed
    assert "title=" not in output


def test_render_xss_in_structural_fields() -> None:
    """
    Verify that HTML injection payloads in structural fields (ID, Title, Description)
    are correctly escaped in the output.
    """
    bad_string = '"><script>alert(1)</script>'
    escaped_string = html.escape(bad_string)

    term = OntologyTerm(id="t1", label="Safe Term", vocab_source="M", code="C", origin=TermOrigin.USER_INPUT)

    # Inject malicious content into description
    block = PicoBlock(block_type="P", description=bad_string, terms=[term])

    # Inject malicious content into Protocol fields
    protocol = ProtocolDefinition(
        id=bad_string,
        title=bad_string,
        research_question=bad_string,
        pico_structure={"P": block},
    )

    output = protocol.render(format="html")

    # The raw bad string should NOT appear (except maybe the alphanumeric parts if we just search substrings)
    # But specifically the tag brackets should be escaped.
    assert "<script>" not in output

    # Verify escaped versions exist
    # ID context: id="..."
    assert f'id="{escaped_string}"' in output

    # Title context: <h2>...</h2>
    # Updated to match new format with (P) suffix
    assert f"<h2>{escaped_string} (P)</h2>" in output

    # Question context: <p>...</p>
    # Note: question is not usually escaped in <p> tag in current implementation?
    # Wait, implementation is <p><strong>Question:</strong> {html.escape(self.research_question)}</p>
    # So it should be present.
    assert escaped_string in output
