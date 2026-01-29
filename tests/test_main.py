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

from coreason_protocol.main import main


@pytest.fixture  # type: ignore[misc]
def protocol_file(tmp_path: object) -> str:
    p = tmp_path / "protocol.json"  # type: ignore
    data = {
        "id": "proto-1",
        "title": "Test Protocol",
        "research_question": "Test Question",
        "pico_structure": {
            "P": {"block_type": "P", "description": "Patients", "terms": [], "logic_operator": "OR"},
            "I": {"block_type": "I", "description": "Intervention", "terms": [], "logic_operator": "OR"},
            "O": {"block_type": "O", "description": "Outcome", "terms": [], "logic_operator": "OR"},
        },
        "status": "DRAFT",
    }
    p.write_text(json.dumps(data))
    return str(p)


def test_main_help(capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "--help"]):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert "coreason-protocol v0.2.0" in captured.out
    assert "usage:" in captured.out


def test_compile_command(protocol_file, capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "compile", protocol_file]):
        # Mock Service to avoid real execution logic dependencies or I/O
        with patch("coreason_protocol.main.ProtocolService") as mock_protocol_service:
            mock_instance = mock_protocol_service.return_value.__enter__.return_value
            mock_instance.compile_protocol.return_value = [MagicMock(target="PUBMED", query_string="QUERY")]

            main()

            # Verify system context was created (implicitly checked by execution flow not crashing)
            # Verify output
            captured = capsys.readouterr()
            assert "Target: PUBMED" in captured.out
            assert "Query: QUERY" in captured.out


def test_validate_command(protocol_file):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "validate", protocol_file]):
        with patch("coreason_protocol.main.ProtocolValidator") as mock_validator:
            main()
            mock_validator.validate.assert_called()


def test_run_command(protocol_file, capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "run", protocol_file]):
        main()
        captured = capsys.readouterr()
        # "Execution logic not implemented yet."
        assert "Execution logic" in captured.out


def test_load_protocol_failure(capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "compile", "non_existent.json"]):
        with pytest.raises(SystemExit):
            main()
    _ = capsys.readouterr()
    # Implicitly covers exception branch in load_protocol -> None -> compile_command exit


def test_validate_command_load_failure(capsys):  # type: ignore[no-untyped-def]
    """Covers line 76: if not protocol check in validate_command."""
    with patch("sys.argv", ["main.py", "validate", "non_existent.json"]):
        with pytest.raises(SystemExit):
            main()
    # load_protocol returns None, validate_command checks if not protocol -> sys.exit(1)


def test_compile_exception(protocol_file):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "compile", protocol_file]):
        with patch("coreason_protocol.main.ProtocolService") as mock_service:
            mock_instance = mock_service.return_value.__enter__.return_value
            mock_instance.compile_protocol.side_effect = Exception("Compile Error")
            with pytest.raises(SystemExit):
                main()


def test_validate_exception(protocol_file):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py", "validate", protocol_file]):
        with patch("coreason_protocol.main.ProtocolValidator") as mock_validator:
            mock_validator.validate.side_effect = Exception("Validation Error")
            with pytest.raises(SystemExit):
                main()


def test_no_command(capsys):  # type: ignore[no-untyped-def]
    with patch("sys.argv", ["main.py"]):
        main()
    captured = capsys.readouterr()
    assert "coreason-protocol v0.2.0" in captured.out
