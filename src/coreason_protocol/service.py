"""Service layer for coreason-protocol."""

from datetime import datetime, timezone
from typing import Any, ContextManager, List, Optional, TypeVar, cast

import anyio
import httpx
from anyio.from_thread import BlockingPortal, start_blocking_portal
from coreason_identity.models import UserContext

from coreason_protocol.utils.logger import logger

from .types import ApprovalRecord, ExecutableStrategy, ProtocolDefinition, ProtocolStatus
from .validator import ProtocolValidator

T = TypeVar("T")


class ProtocolServiceAsync:
    """
    Async Service for Protocol Management.
    Handles I/O and resource management using Dependency Injection.
    """

    def __init__(
        self, client: Optional[httpx.AsyncClient] = None, veritas_url: str = "https://veritas.coreason.ai"
    ) -> None:
        """
        Initialize the service.

        Args:
            client: Optional httpx.AsyncClient. If not provided, one will be created.
            veritas_url: URL of the Veritas service.
        """
        self._internal_client = client is None
        self._client = client or httpx.AsyncClient()
        self._veritas_url = veritas_url

    async def __aenter__(self) -> "ProtocolServiceAsync":
        return self

    async def __aexit__(
        self, exc_type: Optional[type[BaseException]], exc_val: Optional[BaseException], exc_tb: Any
    ) -> None:
        if self._internal_client:
            await self._client.aclose()

    async def lock_protocol(self, protocol: ProtocolDefinition, context: UserContext) -> ProtocolDefinition:
        """
        Finalizes the protocol and registers with Veritas (Async).

        Args:
            protocol: The protocol to lock.
            context: User identity context.

        Returns:
            The updated ProtocolDefinition.
        """
        if context is None:
            raise ValueError("context cannot be None")

        logger.info(
            "Locking protocol",
            user_id=context.user_id,
            protocol_id=str(protocol.id),
        )

        # 1. State Validation
        if protocol.status in (ProtocolStatus.APPROVED, ProtocolStatus.EXECUTED):
            raise ValueError("Cannot lock a protocol that is already APPROVED or EXECUTED")

        if protocol.status != ProtocolStatus.DRAFT:
            raise ValueError(f"Cannot lock protocol in state: {protocol.status}")

        # 2. Structural Validation (CPU-bound)
        await anyio.to_thread.run_sync(ProtocolValidator.validate, protocol)

        # 3. Registration (I/O)
        protocol_data = protocol.model_dump(mode="json")

        try:
            # We assume a simple POST endpoint.
            # In a real scenario, this matches VeritasClient interface logic but over HTTP.
            response = await self._client.post(f"{self._veritas_url}/register", json=protocol_data)
            response.raise_for_status()
            result = response.json()
            # Assuming result is {"hash": "..."} or just the string if it was an interface
            # Based on interfaces.py: register_protocol returns str.
            # Here we assume the API returns JSON with a hash field or similar.
            # Let's assume the API mirrors the return value structure.
            # If interfaces.py says it returns str, maybe the body is just the string?
            # Or a JSON with 'hash'. Let's support a 'hash' key or raw string.
            if isinstance(result, dict) and "hash" in result:
                protocol_hash = result["hash"]
            elif isinstance(result, str):
                protocol_hash = result
            else:
                # Fallback/Edge case
                protocol_hash = str(result)

        except httpx.HTTPError as e:
            # Wrap or re-raise.
            # For compatibility with tests expecting specific behaviors, we might need to adjust.
            raise RuntimeError(f"Failed to register with Veritas: {e}") from e

        # 4. Update Protocol
        protocol.approval_history = ApprovalRecord(
            approver_id=context.user_id,
            timestamp=datetime.now(timezone.utc),
            veritas_hash=protocol_hash,
        )
        protocol.status = ProtocolStatus.APPROVED

        return protocol

    async def compile_protocol(
        self, protocol: ProtocolDefinition, target: str, context: UserContext
    ) -> List[ExecutableStrategy]:
        """
        Compiles the protocol into executable search strategies (Async Wrapper).

        Args:
            protocol: The protocol to compile.
            target: The target execution engine.
            context: User identity context.

        Returns:
            List of ExecutableStrategy.
        """
        if context is None:
            raise ValueError("context cannot be None")

        logger.info(
            "Compiling protocol",
            user_id=context.user_id,
            protocol_id=str(protocol.id),
        )

        # Wrap CPU-heavy compilation
        def _compile_sync() -> List[ExecutableStrategy]:
            return protocol.compile(context=context, target=target)

        # anyio.to_thread.run_sync returns the result of the function, which is List[ExecutableStrategy]
        # Mypy might be confused because run_sync is generic.
        return await anyio.to_thread.run_sync(_compile_sync)


class ProtocolService:
    """
    Sync Facade for ProtocolServiceAsync.
    Bridges Sync -> Async using a persistent portal.
    """

    def __init__(
        self, client: Optional[httpx.AsyncClient] = None, veritas_url: str = "https://veritas.coreason.ai"
    ) -> None:
        self._async_service = ProtocolServiceAsync(client=client, veritas_url=veritas_url)
        self._portal: Optional[BlockingPortal] = None
        self._portal_cm: Optional[ContextManager[BlockingPortal]] = None

    def __enter__(self) -> "ProtocolService":
        # Start a persistent event loop in a background thread
        self._portal_cm = start_blocking_portal()
        self._portal = self._portal_cm.__enter__()
        # Enter the async context (initialize client)
        self._portal.call(self._async_service.__aenter__)
        return self

    def __exit__(self, exc_type: Optional[type[BaseException]], exc_val: Optional[BaseException], exc_tb: Any) -> None:
        if self._portal:
            # Exit async service
            try:
                self._portal.call(self._async_service.__aexit__, exc_type, exc_val, exc_tb)
            finally:
                # Stop the portal
                if self._portal_cm:
                    self._portal_cm.__exit__(exc_type, exc_val, exc_tb)

    def lock_protocol(self, protocol: ProtocolDefinition, context: UserContext) -> ProtocolDefinition:
        """Sync wrapper for lock_protocol."""
        if not self._portal:
            raise RuntimeError("ProtocolService must be used as a context manager (with ... as ...)")
        return cast(ProtocolDefinition, self._portal.call(self._async_service.lock_protocol, protocol, context))

    def compile_protocol(
        self, protocol: ProtocolDefinition, target: str, context: UserContext
    ) -> List[ExecutableStrategy]:
        """Sync wrapper for compile_protocol."""
        if not self._portal:
            raise RuntimeError("ProtocolService must be used as a context manager (with ... as ...)")
        return cast(
            List[ExecutableStrategy],
            self._portal.call(self._async_service.compile_protocol, protocol, target, context),
        )
