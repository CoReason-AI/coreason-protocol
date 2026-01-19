# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from coreason_protocol.types import (
    ApprovalRecord,
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)


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
    assert "Key mismatch in pico_structure" in str(exc.value)


def test_unicode_special_characters() -> None:
    """Verify OntologyTerm handles complex unicode strings."""
    label_unicode = "Ménière's disease & ❤️"
    term = OntologyTerm(id="u1", label=label_unicode, vocab_source="MeSH-JP", code="D123", origin=TermOrigin.USER_INPUT)
    assert term.label == label_unicode

    block = PicoBlock(block_type="P", description="Complex description: 🍎 vs 🍊", terms=[term])

    protocol = ProtocolDefinition(
        id="p1",
        title="Protocol with Emoji",
        research_question="Does 🍎 keep the doctor away?",
        pico_structure={"P": block},
    )

    # Ensure it survives serialization
    json_data = protocol.model_dump_json()
    assert label_unicode in json_data
    assert "🍎" in json_data


def test_json_round_trip() -> None:
    """Verify JSON serialization and deserialization integrity."""
    now = datetime.now(timezone.utc)
    approval = ApprovalRecord(approver_id="admin", timestamp=now, veritas_hash="abc")

    term = OntologyTerm(id="t1", label="Test", vocab_source="S1", code="C1", origin=TermOrigin.SYSTEM_EXPANSION)
    block = PicoBlock(block_type="O", description="Outcome", terms=[term])

    protocol = ProtocolDefinition(
        id="orig",
        title="Original",
        research_question="Q?",
        pico_structure={"O": block},
        status=ProtocolStatus.APPROVED,
        approval_history=approval,
    )

    # Dump to JSON
    json_str = protocol.model_dump_json()

    # Load back
    protocol_loaded = ProtocolDefinition.model_validate_json(json_str)

    assert protocol_loaded.id == protocol.id
    assert protocol_loaded.status == ProtocolStatus.APPROVED
    assert protocol_loaded.approval_history is not None
    assert protocol_loaded.approval_history.timestamp == now
    assert protocol_loaded.pico_structure["O"].terms[0].origin == TermOrigin.SYSTEM_EXPANSION


def test_timezone_awareness() -> None:
    """Verify ApprovalRecord handles timezones correctly."""
    # Create a timezone-aware datetime (e.g., UTC+5:30)
    tz = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2023, 10, 1, 12, 0, 0, tzinfo=tz)

    record = ApprovalRecord(approver_id="u1", timestamp=dt, veritas_hash="h1")

    assert record.timestamp.tzinfo is not None
    assert record.timestamp.utcoffset() == timedelta(hours=5, minutes=30)

    # Round trip via model dump
    dumped = record.model_dump()
    assert dumped["timestamp"] == dt


def test_large_payload() -> None:
    """Stress test with a large number of terms."""
    terms = []
    for i in range(1000):
        terms.append(
            OntologyTerm(
                id=f"t{i}", label=f"Term {i}", vocab_source="Gen", code=f"C{i}", origin=TermOrigin.SYSTEM_EXPANSION
            )
        )

    block = PicoBlock(block_type="P", description="Large Population", terms=terms)

    protocol = ProtocolDefinition(
        id="large_p", title="Large Protocol", research_question="Big Data?", pico_structure={"P": block}
    )

    assert len(protocol.pico_structure["P"].terms) == 1000
    json_str = protocol.model_dump_json()
    assert len(json_str) > 10000  # Rough check that it's big
