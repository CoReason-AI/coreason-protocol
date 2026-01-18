from typing import Any, Dict, Protocol


class VeritasClient(Protocol):
    """Interface for the Coreason Veritas audit system."""

    def register_protocol(self, protocol_data: Dict[str, Any]) -> str:
        """
        Registers the protocol definition with Veritas.

        Args:
            protocol_data: The JSON-serializable dictionary of the protocol.

        Returns:
            str: The hash/signature returned by Veritas.
        """
        ...
