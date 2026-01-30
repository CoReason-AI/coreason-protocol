# Usage Guide

`coreason-protocol` can be used either as a Python library or as a standalone microservice ("Service P").

## 1. Service API Usage

The service exposes a REST API for managing the protocol lifecycle.

### Start the Server

```bash
uvicorn coreason_protocol.server:app --host 0.0.0.0 --port 8000
```

### Endpoints

#### `POST /protocol/draft`

Creates a new protocol draft from a research question.

```bash
curl -X POST "http://localhost:8000/protocol/draft" \
     -H "Content-Type: application/json" \
     -d '{"question": "Does aspirin prevent cancer?"}'
```

**Response:** A JSON object containing the initialized `ProtocolDefinition` with status `DRAFT`.

#### `POST /protocol/lock`

Validates, approves, and locks a protocol. Requires a `user_id` for the audit trail.

```bash
curl -X POST "http://localhost:8000/protocol/lock" \
     -H "Content-Type: application/json" \
     -d '{
           "protocol": { ... protocol_json_object ... },
           "user_id": "user_123"
         }'
```

#### `POST /protocol/compile`

Compiles the protocol into an executable search strategy for a specific target (e.g., `PUBMED`).

```bash
curl -X POST "http://localhost:8000/protocol/compile" \
     -H "Content-Type: application/json" \
     -d '{
           "protocol": { ... protocol_json_object ... },
           "target": "PUBMED",
           "user_id": "user_123"
         }'
```

---

## 2. Library Usage

You can also import `coreason-protocol` directly in your Python code.

```python
from coreason_protocol import ProtocolDefinition, PicoBlock, TermOrigin, OntologyTerm

# Initialize a new Protocol Definition
protocol = ProtocolDefinition(
    id="prot-123",
    title="Statins for CVD Prevention",
    research_question="Do statins reduce CVD risk in elderly patients?",
    pico_structure={},
    status="DRAFT"
)

# Example: Adding a PICO block (programmatically or via AI expansion)
term = OntologyTerm(
    id="term-001",
    label="Statins",
    vocab_source="MeSH",
    code="D019821",
    origin=TermOrigin.USER_INPUT
)

protocol.pico_structure["I"] = PicoBlock(
    block_type="I",
    description="Intervention",
    terms=[term]
)

# Render the protocol for review
html_output = protocol.render(format="html")
print(html_output)
```
