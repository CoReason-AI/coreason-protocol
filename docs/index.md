# Welcome to coreason_protocol

This is the documentation for the coreason_protocol project.

## Features

### Protocol Governance

The `ProtocolDefinition` class enforces a strict state machine for protocol governance.

- **Locking**: The `lock()` method finalizes a protocol, transitioning it from `DRAFT` to `APPROVED`.
- **Validation**: Ensures that the protocol structure is valid (non-empty PICO structure) before locking.
- **Audit**: Registers the protocol with `VeritasClient` to generate an immutable hash and timestamped approval record.
