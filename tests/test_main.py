# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

import json
from unittest.mock import MagicMock, patch

import pytest
from coreason_protocol.main import main, compile_command, validate_command, run_command
from coreason_protocol.types import ProtocolDefinition


@pytest.fixture  # type: ignore[misc]
def protocol_file(tmp_path):  # type: ignore[no-untyped-def]
    p = tmp_path / "protocol.json"
    data = {
        "id": "proto-1",
        "title": "Test Protocol",
        "research_question": "Test Question",
        "pico_structure": {
            "P": {
                "block_type": "P",
                "description": "Patients",
                "terms": [],
                "logic_operator": "OR"
            },
            "I": {
                "block_type": "I",
                "description": "Intervention",
                "terms": [],
                "logic_operator": "OR"
            },
             "O": {
                "block_type": "O",
                "description": "Outcome",
                "terms": [],
                "logic_operator": "OR"
            }
        },
        "status": "DRAFT"
    }
    p.write_text(json.dumps(data))
    return str(p)


def test_main_help(capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "--help"]):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert "usage:" in captured.out


def test_compile_command(protocol_file, capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "compile", protocol_file]):
        # Mock Service to avoid real execution logic dependencies or I/O
        with patch("coreason_protocol.main.ProtocolService") as MockService:
            mock_instance = MockService.return_value.__enter__.return_value
            mock_instance.compile_protocol.return_value = [
                MagicMock(target="PUBMED", query_string="QUERY")
            ]

            main()

            # Verify system context was created (implicitly checked by execution flow not crashing)
            # Verify output
            captured = capsys.readouterr()
            assert "Target: PUBMED" in captured.out
            assert "Query: QUERY" in captured.out


def test_validate_command(protocol_file):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "validate", protocol_file]):
        with patch("coreason_protocol.main.ProtocolValidator") as MockValidator:
             main()
             MockValidator.validate.assert_called()


def test_run_command(protocol_file, capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "run", protocol_file]):
        main()
        captured = capsys.readouterr()
        # "Execution logic not implemented yet."
        assert "Execution logic" in captured.out
