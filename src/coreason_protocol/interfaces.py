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


class VeritasClient(Protocol):
    """Interface for the Coreason-Veritas audit log service."""

    def register_protocol(self, payload: Dict[str, Any]) -> str:
        """
        Registers a protocol definition with the audit log.

        Args:
            payload: The protocol definition data to register.

        Returns:
            str: The hash returned by the audit service.
        """
        ...
