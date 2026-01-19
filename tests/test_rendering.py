import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


def test_render_unsupported_format() -> None:
    pd = ProtocolDefinition(id="1", title="T", research_question="Q", pico_structure={}, status=ProtocolStatus.DRAFT)
    with pytest.raises(ValueError, match="Unsupported format: text"):
        pd.render(format="text")


def test_render_html_basic_structure() -> None:
    pd = ProtocolDefinition(
        id="proto-1",
        title="Test Protocol",
        research_question="Does X cause Y?",
        pico_structure={},
        status=ProtocolStatus.DRAFT,
    )
    html_output = pd.render()
    assert "<h1>Protocol: Test Protocol</h1>" in html_output
    assert "<strong>ID:</strong> proto-1" in html_output
    assert "<strong>Question:</strong> Does X cause Y?" in html_output


def test_render_term_styles() -> None:
    # 1. User Input (Blue/Bold)
    t1 = OntologyTerm(id="1", label="User Term", vocab_source="Src", code="C1", origin=TermOrigin.USER_INPUT)
    # 2. System Expansion (Grey/Italic)
    t2 = OntologyTerm(id="2", label="Sys Term", vocab_source="Src", code="C2", origin=TermOrigin.SYSTEM_EXPANSION)
    # 3. Human Injection (Blue/Bold)
    t3 = OntologyTerm(id="3", label="Inj Term", vocab_source="Src", code="C3", origin=TermOrigin.HUMAN_INJECTION)
    # 4. Inactive (Red/Strike)
    t4 = OntologyTerm(
        id="4",
        label="Del Term",
        vocab_source="Src",
        code="C4",
        origin=TermOrigin.SYSTEM_EXPANSION,
        is_active=False,
        override_reason="Bad match",
    )

    block = PicoBlock(block_type="P", description="Pop", terms=[t1, t2, t3, t4])
    pd = ProtocolDefinition(
        id="1", title="T", research_question="Q", pico_structure={"P": block}, status=ProtocolStatus.DRAFT
    )

    html_output = pd.render()

    # Check t1
    assert '<b style="color: blue">User Term</b>' in html_output
    # Check t2
    assert '<i style="color: grey">Sys Term</i>' in html_output
    # Check t3
    assert '<b style="color: blue">Inj Term</b>' in html_output
    # Check t4
    assert "style='color: red; text-decoration: line-through;'" in html_output
    assert 'title="Reason: Bad match"' in html_output
    assert ">Del Term</span>" in html_output


def test_render_xss_prevention() -> None:
    malicious_title = "<script>alert('XSS')</script>"
    malicious_term = "Term <img src=x onerror=alert(1)>"

    t1 = OntologyTerm(id="1", label=malicious_term, vocab_source="S", code="C", origin=TermOrigin.USER_INPUT)
    block = PicoBlock(block_type="P", description="Pop", terms=[t1])

    pd = ProtocolDefinition(
        id="1", title=malicious_title, research_question="Q", pico_structure={"P": block}, status=ProtocolStatus.DRAFT
    )

    html_output = pd.render()

    # Ensure tags are escaped. Note: html.escape escapes single quotes to &#x27;
    assert "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in html_output
    assert "<script>" not in html_output

    # Ensure term label is escaped
    assert "Term &lt;img src=x onerror=alert(1)&gt;" in html_output
    assert "<img" not in html_output


def test_render_block_ordering() -> None:
    """Ensure blocks are rendered in P, I, C, O, S order regardless of dict insertion order."""
    t = OntologyTerm(id="1", label="T", vocab_source="S", code="C", origin=TermOrigin.USER_INPUT)

    b_o = PicoBlock(block_type="O", description="Out", terms=[t])
    b_p = PicoBlock(block_type="P", description="Pop", terms=[t])

    pd = ProtocolDefinition(
        id="1",
        title="T",
        research_question="Q",
        pico_structure={"O": b_o, "P": b_p},  # Insert O before P
        status=ProtocolStatus.DRAFT,
    )

    html_output = pd.render()

    # Updated expectation due to header format change
    idx_p = html_output.find("<h2>Pop (P)</h2>")
    idx_o = html_output.find("<h2>Out (O)</h2>")

    assert idx_p != -1
    assert idx_o != -1
    assert idx_p < idx_o  # P should come before O
