# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol


import pytest

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


# Helper to create a simple term
def create_term(term_id: str, label: str) -> OntologyTerm:
    return OntologyTerm(
        id=term_id,
        label=label,
        vocab_source="MeSH",
        code=f"D{term_id}",
        origin=TermOrigin.SYSTEM_EXPANSION,
    )


@pytest.fixture
def complex_protocol() -> ProtocolDefinition:
    """
    Creates a fully populated PICO protocol with multiple blocks and terms.
    Structure:
      P: p1, p2
      I: i1
      C: c1, c2 (Target for test), c3
      O: o1
    """
    p_block = PicoBlock(
        block_type="P", description="Population", terms=[create_term("p1", "Pop1"), create_term("p2", "Pop2")]
    )
    i_block = PicoBlock(block_type="I", description="Intervention", terms=[create_term("i1", "Int1")])
    c_block = PicoBlock(
        block_type="C",
        description="Comparator",
        terms=[create_term("c1", "Comp1"), create_term("c2", "Comp2"), create_term("c3", "Comp3")],
    )
    o_block = PicoBlock(block_type="O", description="Outcome", terms=[create_term("o1", "Out1")])

    return ProtocolDefinition(
        id="proto-complex",
        title="Complex Protocol",
        research_question="Complex Q?",
        pico_structure={
            "P": p_block,
            "I": i_block,
            "C": c_block,
            "O": o_block,
        },
        status=ProtocolStatus.DRAFT,
    )


class TestOverrideTermComplex:
    def test_override_term_multi_block_isolation(self, complex_protocol: ProtocolDefinition) -> None:
        """
        Scenario: In a multi-block protocol, override a term deeply nested in the 'C' block.
        Verify:
        1. The target term (c2) is soft-deleted.
        2. Neighbors in the same block (c1, c3) are UNTOUCHED.
        3. Terms in other blocks (p1, i1, o1) are UNTOUCHED.
        """
        target_id = "c2"
        reason = "Not relevant comparator"

        # Action
        complex_protocol.override_term(target_id, reason)

        # Assertions

        # 1. Target checks
        c_terms = complex_protocol.pico_structure["C"].terms
        target_term = next(t for t in c_terms if t.id == target_id)
        assert target_term.is_active is False
        assert target_term.override_reason == reason

        # 2. Neighbor checks (Same block)
        neighbor_c1 = next(t for t in c_terms if t.id == "c1")
        neighbor_c3 = next(t for t in c_terms if t.id == "c3")
        assert neighbor_c1.is_active is True
        assert neighbor_c3.is_active is True
        assert neighbor_c1.override_reason is None

        # 3. Cross-block checks
        p_terms = complex_protocol.pico_structure["P"].terms
        assert p_terms[0].is_active is True  # p1

        i_terms = complex_protocol.pico_structure["I"].terms
        assert i_terms[0].is_active is True  # i1

    def test_re_override_updates_reason(self, complex_protocol: ProtocolDefinition) -> None:
        """
        Scenario: A user overrides a term, then realizes the reason was vague and overrides it again.
        Verify:
        1. Term remains inactive.
        2. Reason is UPDATED to the new string.
        """
        target_id = "p1"

        # First pass
        complex_protocol.override_term(target_id, "Typo reason")
        term = complex_protocol.pico_structure["P"].terms[0]
        assert term.override_reason == "Typo reason"
        assert term.is_active is False

        # Second pass (Correction)
        new_reason = "Corrected: Population too specific"
        complex_protocol.override_term(target_id, new_reason)

        # Verify update
        assert term.override_reason == new_reason
        assert term.is_active is False

    def test_override_reason_unicode_integrity(self, complex_protocol: ProtocolDefinition) -> None:
        """
        Scenario: User provides a reason with complex Unicode characters (Emojis, CJK, etc.).
        Verify: The system stores it exactly as provided (Audit fidelity).
        """
        target_id = "i1"
        # Greek, Emoji, Chinese, SQL-like injection chars
        complex_reason = "α-blockers rejected 🚫 due to side effects (副作用); SELECT * FROM users;"

        complex_protocol.override_term(target_id, complex_reason)

        term = complex_protocol.pico_structure["I"].terms[0]
        assert term.override_reason == complex_reason
