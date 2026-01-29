# Requirements

The `coreason-protocol` service requires the following Python dependencies:

*   **python**: `>=3.11, <3.15`
*   **pydantic**: `^2.0` (Data validation)
*   **loguru**: `^0.7.0` (Logging)
*   **boolean-py**: `^5.0` (Boolean logic parsing)
*   **anyio**: `^4.12.1` (Asynchronous I/O)
*   **httpx**: `^0.28.1` (HTTP client)
*   **aiofiles**: `^25.1.0` (Async file operations)
*   **coreason-identity**: `^0.4.2` (Identity management context)
*   **fastapi**: `*` (API Framework)
*   **uvicorn[standard]**: `*` (ASGI Server)

## Development Dependencies

For testing and development:

*   **pytest**: `^9.0.2`
*   **pytest-cov**: `^7.0.0`
*   **mypy**: `^1.8`
*   **ruff**: `^0.14.14`
*   **types-aiofiles**: `^25.1.0`
*   **pytest-asyncio**: `^1.3.0`
*   **mkdocs**: `^1.5.0`
*   **mkdocs-material**: `^9.0.0`
