# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

import coreason_protocol
from coreason_protocol.main import main


def test_package_exports() -> None:
    # Verify we can access classes from the top level
    assert coreason_protocol.ProtocolDefinition is not None
    assert coreason_protocol.OntologyTerm is not None
    assert coreason_protocol.StrategyCompiler is not None
    assert coreason_protocol.VeritasClient is not None


def test_main(capsys) -> None:  # type: ignore[no-untyped-def]
    main()
    captured = capsys.readouterr()
    assert "coreason-protocol v0.1.0" in captured.out
