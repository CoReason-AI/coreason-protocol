# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from coreason_protocol.utils.logger import logger


def test_hello_world() -> None:
    """Test the hello world function."""
    assert logger is not None
    # We can't really test the log output without capturing stderr,
    # but we can ensure the logger import works.
