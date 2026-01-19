# Coreason Protocol

![License](https://img.shields.io/badge/License-Prosperity%203.0-blue)
[![Build Status](https://github.com/CoReason-AI/coreason-protocol/actions/workflows/build.yml/badge.svg)](https://github.com/CoReason-AI/coreason-protocol/actions)
[![Code Style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**The Design and Governance Engine for Systematic Review Design.**

`coreason-protocol` is the "Study Director" for high-stakes research. It transforms natural language intent into a rigorous, audited, and executable search protocol. Unlike simple RAG retrieval, it enforces a scientific workflow where AI creates a draft (using PICO and Ontology expansion), but a Human Expert must validate, modify, and digitally sign off on the strategy before execution.

## Features

- **PICO Architecture:** Deconstructs user intent into Population, Intervention, Comparator, and Outcome blocks.
- **Ontological Expansion:** Hydrates terms with Concept IDs using `coreason-codex` to ensure comprehensive coverage.
- **PRESS Validation:** Checks draft strategies against Peer Review of Electronic Search Strategies (PRESS) guidelines.
- **Human-in-the-Loop Governance:** Supports `override_term` and `inject_term` actions with full audit trails (reason codes, timestamps).
- **Polyglot Compilation:** Compiles protocols into executable code for multiple backends:
    - **PubMed/Ovid:** Generates complex Boolean strings with MeSH/TiAb handling.
    - **LanceDB:** Generates vector embedding requests and metadata filters.
    - **Graph (Cypher):** Generates traversal logic for graph databases.
- **Immutable Registration:** Locks protocols with a Veritas hash upon approval, ensuring regulatory compliance.
- **Multi-Format Rendering:** Exports protocols as interactive HTML with color-coded provenance (User Input vs. AI Expansion vs. Human Injection).

## Installation

```bash
pip install coreason-protocol
```

## Usage

```python
from coreason_protocol import ProtocolDefinition, TermOrigin, OntologyTerm, PicoBlock
from datetime import datetime

# 1. Define a PICO structure (usually done by AI)
pico = {
    "P": PicoBlock(
        block_type="P",
        description="Elderly Patients",
        terms=[
            OntologyTerm(
                id="uuid-1",
                label="Aged",
                vocab_source="MeSH",
                code="D000368",
                origin=TermOrigin.SYSTEM_EXPANSION
            )
        ]
    ),
    "I": PicoBlock(
        block_type="I",
        description="Aspirin",
        terms=[
            OntologyTerm(
                id="uuid-2",
                label="Aspirin",
                vocab_source="MeSH",
                code="D001241",
                origin=TermOrigin.USER_INPUT
            )
        ]
    ),
    "O": PicoBlock(
        block_type="O",
        description="Stroke Prevention",
        terms=[
             OntologyTerm(
                id="uuid-3",
                label="Stroke",
                vocab_source="MeSH",
                code="D020521",
                origin=TermOrigin.SYSTEM_EXPANSION
            )
        ]
    )
}

# 2. Create the Protocol Definition
protocol = ProtocolDefinition(
    id="protocol-123",
    title="Aspirin for Stroke in Elderly",
    research_question="Does aspirin prevent stroke in elderly patients?",
    pico_structure=pico
)

# 3. Compile for PubMed
strategies = protocol.compile(target="PUBMED")
print(strategies[0].query_string)
# Output: ("Aged"[Mesh]) AND ("Aspirin"[Mesh]) AND ("Stroke"[Mesh])

# 4. Render as HTML for review
html_output = protocol.render(format="html")
```
