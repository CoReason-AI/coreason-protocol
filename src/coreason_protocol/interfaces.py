# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from typing import Any, Dict, Protocol


class VeritasClientProtocol(Protocol):
    """Protocol for the Veritas Audit System client."""

    def hash_and_register(self, data: Dict[str, Any]) -> str:
        """
        Hashes the data and registers it to the immutable ledger.
        Returns the hash string.
        """
        ...
