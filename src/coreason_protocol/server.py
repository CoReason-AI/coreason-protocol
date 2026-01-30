import uuid
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator, List

from coreason_identity.models import UserContext
from fastapi import Body, FastAPI, HTTPException, Request

from coreason_protocol.service import ProtocolServiceAsync
from coreason_protocol.types import ExecutableStrategy, ProtocolDefinition, ProtocolStatus


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for the API."""
    service = ProtocolServiceAsync()
    await service.__aenter__()
    app.state.service = service
    try:
        yield
    finally:
        await service.__aexit__(None, None, None)


app = FastAPI(lifespan=lifespan)


@app.get("/health")  # type: ignore[misc]
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0", "role": "design_plane"}


@app.post("/protocol/draft")  # type: ignore[misc]
async def draft_protocol(
    question: Annotated[str, Body(embed=True)],
) -> ProtocolDefinition:
    """
    Initializes a ProtocolDefinition in DRAFT status from a research question.
    """
    # Simulated PICO extraction
    protocol = ProtocolDefinition(
        id=str(uuid.uuid4()),
        title="Draft Protocol",
        research_question=question,
        pico_structure={},
        execution_strategies=[],
        status=ProtocolStatus.DRAFT,
    )
    return protocol


@app.post("/protocol/lock")  # type: ignore[misc]
async def lock_protocol(
    request: Request,
    protocol: Annotated[ProtocolDefinition, Body(...)],
    user_id: Annotated[str, Body(...)],
) -> ProtocolDefinition:
    """
    Finalizes the protocol and registers with Veritas.
    """
    service: ProtocolServiceAsync = request.app.state.service

    # Create UserContext from user_id
    context = UserContext(
        user_id=user_id,
        email="api-user@coreason.ai",
        groups=["api_user"],
        scopes=[],
        claims={},
    )

    try:
        updated_protocol = await service.lock_protocol(protocol, context)
        return updated_protocol
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/protocol/compile")  # type: ignore[misc]
async def compile_protocol(
    request: Request,
    protocol: Annotated[ProtocolDefinition, Body(...)],
    target: Annotated[str, Body(...)],
    user_id: Annotated[str, Body()] = "api-user",
) -> List[ExecutableStrategy]:
    """
    Compiles the protocol into executable search strategies.
    """
    service: ProtocolServiceAsync = request.app.state.service

    # Create UserContext from user_id
    context = UserContext(
        user_id=user_id,
        email="api-user@coreason.ai",
        groups=["api_user"],
        scopes=[],
        claims={},
    )

    strategies = await service.compile_protocol(protocol, target, context)
    return strategies
