# coreason-protocol

The **Design and Governance Engine** for high-stakes research.

[![Organization](https://img.shields.io/badge/org-CoReason--AI-blue)](https://github.com/CoReason-AI)
[![License](https://img.shields.io/badge/license-Prosperity%203.0-blue)](https://github.com/CoReason-AI/coreason-protocol/blob/main/LICENSE)
[![Build Status](https://github.com/CoReason-AI/coreason-protocol/actions/workflows/build.yml/badge.svg)](https://github.com/CoReason-AI/coreason-protocol/actions)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Documentation](https://img.shields.io/badge/docs-product_requirements.md-blue)](docs/product_requirements.md)

## Description

`coreason-protocol` transforms natural language intent into a **Rigorous, Audited, and Executable Search Protocol**. It acts as the "Study Director" or Design Plane, ensuring that research protocols are designed with rigor, validated with logic (PRESS guidelines), and approved with authority before execution.

Unlike simple RAG retrieval, this package enforces a scientific workflow:
1.  **AI Draft:** Generates PICO blocks and expands terms using ontologies (via `coreason-codex`).
2.  **Human Governance:** Allows experts to override or inject terms.
3.  **Strict Validation:** Checks structural integrity and PRESS guidelines.
4.  **Immutable Registration:** Locks and registers approved protocols (via `coreason-veritas`).

## Service Architecture (Service P)

`coreason-protocol` can be deployed as a microservice ("Service P") exposing a FastAPI-based REST API. This service handles the lifecycle of the protocol, from drafting to compilation, while integrating with the Veritas audit system.

For details on API endpoints and usage, see [Usage Guide](docs/usage.md).

## Installation

```bash
pip install coreason-protocol
```

Or using poetry:

```bash
poetry add coreason-protocol
```

## Dependencies

For a full list of dependencies, see [Requirements](docs/requirements.md).

## Features

*   **PICO Architecture:** Structuring of research intent into Population, Intervention, Comparator, and Outcome.
*   **Ontology Expansion:** Integration with `coreason-codex` for term hydration (Concept IDs).
*   **Strategy Compilation:** Translation of PICO models into executable queries for:
    *   PubMed/Ovid (Boolean strings with MeSH/TiAb mapping).
    *   LanceDB (Vector embeddings + metadata filters).
    *   Graph (Cypher queries).
*   **HITL Governance:** Support for human review with `override_term` and `inject_term` capabilities.
*   **Audit Fidelity:** Soft-deletion of terms to maintain a complete history of design decisions.
*   **Multi-Format Rendering:** Export to HTML (visual diff), PRISMA-S text, and JSON-LD.

## Documentation

For detailed product requirements and architectural philosophy, see [docs/product_requirements.md](docs/product_requirements.md).
