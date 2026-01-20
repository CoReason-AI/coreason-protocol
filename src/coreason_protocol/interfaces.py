"""Interfaces for external dependencies."""

from typing import Any, Dict, Protocol


class VeritasClient(Protocol):
    """Interface for the Coreason Veritas audit system.

    This protocol defines the contract for interacting with the Veritas
    immutable audit log.
    """

    def register_protocol(self, protocol_data: Dict[str, Any]) -> str:
        """Registers the protocol definition with Veritas.

        Args:
            protocol_data: The JSON-serializable dictionary of the protocol definition.

        Returns:
            str: The immutable cryptographic hash/signature returned by Veritas.
        """
        ...
