# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from datetime import datetime
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from coreason_protocol.types import (
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


class MockVeritasClient:
    """Mock implementation of VeritasClientProtocol for testing."""

    def hash_and_register(self, data: Dict[str, Any]) -> str:
        return "hash_12345"


def test_pico_structure_key_mismatch() -> None:
    """Verify validation fails when pico_structure key does not match block_type."""
    term = OntologyTerm(
        id="123", label="Heart Attack", vocab_source="MeSH", code="D009203", origin=TermOrigin.USER_INPUT
    )
    # Block type is "P"
    block = PicoBlock(block_type="P", description="Population", terms=[term])

    with pytest.raises(ValidationError) as exc:
        ProtocolDefinition(
            id="proto_1",
            title="My Protocol",
            research_question="Q",
            # Mismatch: key "I" != block_type "P"
            pico_structure={"I": block},
        )

    # This assertion comes from the user's log
    assert "Key mismatch in pico_structure" in str(exc.value)


def test_unicode_handling() -> None:
    """Test that the protocol handles non-ASCII characters correctly in all fields."""
    unicode_term = OntologyTerm(
        id="u1",
        label="心筋梗塞 (Myocardial Infarction)",
        vocab_source="J-MeSH",
        code="D009203",
        origin=TermOrigin.SYSTEM_EXPANSION,
    )

    block = PicoBlock(block_type="P", description="Patients with 👴 elderly conditions", terms=[unicode_term])

    protocol = ProtocolDefinition(
        id="proto_unicode",
        title="Protocol for ⚕️ Medical Research",
        research_question="Effect of 🍵 Green Tea",
        pico_structure={"P": block},
    )

    # Render and check if characters are preserved (and escaped if needed)
    html_output = protocol.render(format="html")

    assert "Protocol for ⚕️ Medical Research" in html_output
    assert "Patients with 👴 elderly conditions" in html_output
    assert "心筋梗塞 (Myocardial Infarction)" in html_output

    # Check lock/hashing (mocked)
    client = MockVeritasClient()
    protocol.lock("user_unicode", client)
    assert protocol.status == ProtocolStatus.APPROVED


def test_large_payload_performance() -> None:
    """Test handling of a large number of terms to ensure no recursion limits or crash."""
    terms = []
    for i in range(1000):
        terms.append(
            OntologyTerm(
                id=f"t{i}", label=f"Term {i}", vocab_source="MeSH", code=f"D{i:06d}", origin=TermOrigin.SYSTEM_EXPANSION
            )
        )

    block = PicoBlock(block_type="I", description="Large Intervention Set", terms=terms)

    protocol = ProtocolDefinition(
        id="proto_large", title="Large Protocol", research_question="Big Data", pico_structure={"I": block}
    )

    # Ensure validation passes rapidly
    assert len(protocol.pico_structure["I"].terms) == 1000

    # Render
    start = datetime.now()
    html_output = protocol.render(format="html")
    end = datetime.now()

    # Basic performance sanity check (should be sub-second for 1000 items)
    assert (end - start).total_seconds() < 1.0
    assert "Term 999" in html_output


def test_timezone_aware_timestamp() -> None:
    """Test that the timestamp generated during lock is timezone-aware (UTC)."""
    client = MockVeritasClient()

    term = OntologyTerm(id="1", label="A", vocab_source="B", code="C", origin=TermOrigin.USER_INPUT)
    block = PicoBlock(block_type="O", description="Outcome", terms=[term])

    protocol = ProtocolDefinition(id="proto_tz", title="TZ Test", research_question="Q", pico_structure={"O": block})

    protocol.lock("user_tz", client)

    assert protocol.approval_history is not None
    ts = protocol.approval_history.timestamp

    # Check it has timezone info
    assert ts.tzinfo is not None

    # Verify UTC offset safely
    offset = ts.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0
