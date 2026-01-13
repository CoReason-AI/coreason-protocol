import html

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    TermOrigin,
)


def test_render_unicode_and_symbols() -> None:
    """Test rendering of Unicode characters and symbols."""
    term = OntologyTerm(
        id="t1",
        label="Naïve T-Cells & β-blockers",
        vocab_source="MeSH",
        code="D123",
        origin=TermOrigin.USER_INPUT,
    )
    block = PicoBlock(block_type="P", description="Complex Chars", terms=[term])

    protocol = ProtocolDefinition(
        id="proto-unicode",
        title="Study of 'Ménière's disease'",
        research_question="H₂O vs CO₂?",
        pico_structure={"P": block},
    )

    output = protocol.render(format="html")

    # Title should be escaped (quotes)
    expected_title_fragment = "Study of &#x27;Ménière&#x27;s disease&#x27;"
    assert expected_title_fragment in output or html.escape(protocol.title) in output

    # Term label should be present.
    # html.escape usually preserves unicode chars but escapes & < > " '
    # "Naïve T-Cells & β-blockers" -> "Naïve T-Cells &amp; β-blockers"
    assert "Naïve T-Cells &amp; β-blockers" in output
    assert "H₂O vs CO₂?" in output


def test_render_complex_reason_escaping() -> None:
    """Test that override reasons with quotes are safely escaped in attributes."""
    term = OntologyTerm(
        id="t1",
        label="Placebo",
        vocab_source="MeSH",
        code="D000",
        origin=TermOrigin.SYSTEM_EXPANSION,
        is_active=False,
        # Reason contains double quotes, single quotes, and angle brackets
        override_reason='Reviewer said "NO" to <Placebo>',
    )
    block = PicoBlock(block_type="C", description="Comparator", terms=[term])

    protocol = ProtocolDefinition(
        id="proto-escape",
        title="Escape Test",
        research_question="?",
        pico_structure={"C": block},
    )

    output = protocol.render(format="html")

    # We expect title="Reason: Reviewer said &quot;NO&quot; to &lt;Placebo&gt;"
    # Exact escaping of single quotes might vary by python version default,
    # but double quotes must be escaped for attribute safety.
    expected_title_attr = 'title="Reason: Reviewer said &quot;NO&quot; to &lt;Placebo&gt;"'
    assert expected_title_attr in output


def test_render_empty_terms_block() -> None:
    """Test rendering of a block with no terms."""
    block = PicoBlock(block_type="I", description="Empty Intervention", terms=[])

    protocol = ProtocolDefinition(
        id="proto-empty-terms",
        title="Empty Terms Test",
        research_question="?",
        pico_structure={"I": block},
    )

    output = protocol.render(format="html")

    assert "Empty Intervention (I)" in output
    assert "<ul>" in output
    assert "</ul>" in output
    # Should not contain any <li>
    assert "<li>" not in output


def test_render_full_complex_protocol() -> None:
    """
    Test a complex scenario with multiple blocks, mixed origins, and statuses.
    Simulates a realistic systematic review protocol.
    """
    p_block = PicoBlock(
        block_type="P",
        description="Population",
        terms=[
            OntologyTerm(
                id="p1",
                label="Pregnant Women",
                vocab_source="MeSH",
                code="D011247",
                origin=TermOrigin.USER_INPUT,
            ),
            OntologyTerm(
                id="p2",
                label="Pregnancy",
                vocab_source="MeSH",
                code="D011247",
                origin=TermOrigin.SYSTEM_EXPANSION,
            ),
        ],
    )

    i_block = PicoBlock(
        block_type="I",
        description="Intervention",
        terms=[
            OntologyTerm(
                id="i1",
                label="mRNA Vaccines",
                vocab_source="RxNorm",
                code="123",
                origin=TermOrigin.USER_INPUT,
            ),
            OntologyTerm(
                id="i2",
                label="BNT162b2",
                vocab_source="RxNorm",
                code="456",
                origin=TermOrigin.SYSTEM_EXPANSION,
            ),
            # Inactive term with reason
            OntologyTerm(
                id="i3",
                label="Moderna",
                vocab_source="RxNorm",
                code="789",
                origin=TermOrigin.SYSTEM_EXPANSION,
                is_active=False,
                override_reason="Duplicate concept",
            ),
            # Human Injection
            OntologyTerm(
                id="i4", label="Spikevax", vocab_source="Custom", code="C1", origin=TermOrigin.HUMAN_INJECTION
            ),
        ],
    )

    protocol = ProtocolDefinition(
        id="proto-complex",
        title="Complex COVID-19 Protocol",
        research_question="Safety of mRNA vaccines in pregnancy?",
        pico_structure={"P": p_block, "I": i_block},
    )

    output = protocol.render(format="html")

    # Check Header
    assert "Complex COVID-19 Protocol" in output

    # Check Population Terms
    # User Input -> Blue/Bold
    assert '<b style="color: blue">Pregnant Women</b>' in output
    # System -> Grey/Italics
    assert '<i style="color: grey">Pregnancy</i>' in output

    # Check Intervention Terms
    # User
    assert '<b style="color: blue">mRNA Vaccines</b>' in output
    # Active System
    assert '<i style="color: grey">BNT162b2</i>' in output
    # Inactive System -> Red, Strikethrough, Tooltip
    assert "Moderna" in output
    assert "color: red" in output
    assert "text-decoration: line-through" in output
    assert 'title="Reason: Duplicate concept"' in output
    # Human Injection -> Blue/Bold
    assert '<b style="color: blue">Spikevax</b>' in output

    # Verify Structure Order (roughly)
    # We can't guarantee dict iteration order in all python versions/implementations strictly,
    # but P and I keys should be present.
    assert "Population (P)" in output
    assert "Intervention (I)" in output
