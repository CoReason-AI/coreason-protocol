# Product Requirements Document: coreason-protocol

**Domain:** Systematic Review Design, PICO Governance, & Regulatory Sign-Off
**Architectural Role:** The "Study Director" / The Design Plane
**Core Philosophy:** "The Protocol is the Law. Design with rigor, validate with logic, approve with authority."
**Dependencies:** `coreason-codex` (Terminology), `coreason-validator` (Schemas), `coreason-veritas` (Audit), `coreason-human-layer` (Review UI)

---

## 1. Executive Summary

`coreason-protocol` is the **Design and Governance Engine** for high-stakes research.

Its purpose is to transform a natural language intent into a **Rigorous, Audited, and Executable Search Protocol**. Unlike simple RAG retrieval, `coreason-protocol` enforces a scientific workflow where AI creates a draft (using PICO and Ontology expansion), but a **Human Expert** must validate, modify, and digitally sign off on the strategy before execution.

The package outputs a **ProtocolDefinition**—a portable JSON artifact that tracks the lineage of the design (User Input $\to$ AI Expansion $\to$ Human Override $\to$ Final Approval), renders it for display, and compiles it for the `coreason-search` execution engine.

## 2. Functional Philosophy

The agent must implement the **Design-Validate-Review-Register Loop**:

1.  **Semantic Deconstruction (PICO):** The AI parses user intent into **P**opulation, **I**ntervention, **C**omparator, **O**utcome blocks.
2.  **Ontological Expansion (SOTA):** Uses `coreason-codex` to hydrate terms with Concept IDs (e.g., mapping "Heart Attack" $\to$ MeSH:D009203 and its children).
3.  **PRESS Validation:** Before human review, the draft is checked against **PRESS Guidelines** (Peer Review of Electronic Search Strategies) to catch logical errors (e.g., "AND" used incorrectly within a synonym block).
4.  **HITL Governance:** The protocol pauses for human review. The user can **Override** AI choices (remove synonyms) or **Inject** new terms via `coreason-human-layer`.
5.  **Immutable Registration:** Upon Human Sign-off, the protocol is hashed and logged to `coreason-veritas`. Only APPROVED protocols are valid inputs for `coreason-search`.

---

## 3. Core Functional Requirements (Component Level)

### 3.1 The PICO Architect (The Designer)
**Concept:** The AI engine that creates the "First Draft."

*   **Mechanism:**
    *   Extracts P, I, C, O, and S (Study Design) from natural language.
    *   Calls `coreason-codex` to expand terms using the CONCEPT_ANCESTOR hierarchy.
    *   **Traceability:** Tags every term with `origin="SYSTEM_EXPANSION"` or `origin="USER_INPUT"`.

### 3.2 The Strategy Compiler (The Translator)
**Concept:** Converts the abstract PICO model into executable code for specific backends.

*   **Polyglot Output:**
    *   **PubMed/Ovid:** Generates complex Boolean strings: `("Term A"[Mesh] OR "Term B"[TiAb])`.
    *   **LanceDB (Vector):** Generates embedding request + metadata filters: `{"vector": embed("query"), "filter": "year > 2020"}`.
    *   **Graph (Cypher):** Generates traversal logic for `coreason-graph-nexus`.

### 3.3 The Review Manager (The HITL Engine)
**Concept:** Manages the editing and approval state.

*   **Capabilities:**
    *   `override_term()`: Soft-deletes a synonym suggested by AI (requires a `reason_code`).
    *   `inject_term()`: Adds a manual keyword missed by the ontology.
    *   `sign_off()`: Validates the structure, generates a hash, calls veritas, and locks the object state.

### 3.4 The Multi-Format Renderer (The Presenter)
**Concept:** Converts the internal object into standard viewing formats.

*   **Formats:**
    *   **Interactive HTML:** Color-coded visualization (Blue=User, Grey=AI, Red=Deleted).
    *   **PRISMA-S Text:** Generates the "Search Strategy" text block for manuscript methods sections.
    *   **JSON-LD:** For interoperability with external evidence synthesis tools.

---

## 4. Integration Requirements

*   **coreason-codex:**
    *   **Relation:** The source of truth. protocol queries codex to validate that every term exists in a standard vocabulary.
*   **coreason-human-layer:**
    *   **Relation:** The UI. protocol provides the `render()` output to the UI and accepts override commands from it.
*   **coreason-veritas:**
    *   **Relation:** The Audit Log. Upon `sign_off()`, the ProtocolDefinition is hashed and registered.
*   **coreason-search:**
    *   **Relation:** The Consumer. search accepts the `ProtocolDefinition`. It checks `status="APPROVED"` and verifies the Veritas hash before executing.

---

## 5. Data Schema (The Deliverable)

### 5.1 Ontology & PICO Elements

```python
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TermOrigin(str, Enum):
    USER_INPUT = "USER_INPUT"           # The user typed this
    SYSTEM_EXPANSION = "SYSTEM_EXPANSION" # Codex added this (Ontology child)
    HUMAN_INJECTION = "HUMAN_INJECTION"   # Reviewer added this manually

class OntologyTerm(BaseModel):
    id: str                             # UUID
    label: str                          # "Myocardial Infarction"
    vocab_source: str                   # "MeSH"
    code: str                           # "D009203"
    origin: TermOrigin
    is_active: bool = True              # False if soft-deleted by human
    override_reason: Optional[str]      # e.g., "Term captures non-human studies"

class PicoBlock(BaseModel):
    block_type: str                     # "P", "I", "C", "O", "S"
    description: str                    # "Elderly Patients"
    terms: List[OntologyTerm]           # The curated list of terms
    logic_operator: str = "OR"          # Logic intra-block
```

### 5.2 Execution & Governance

```python
class ProtocolStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"               # Locked & Registered
    EXECUTED = "EXECUTED"

class ExecutableStrategy(BaseModel):
    target: str                         # "PUBMED", "LANCEDB"
    query_string: str                   # The compiled code string
    validation_status: str              # "PRESS_PASSED" or "WARNINGS"

class ApprovalRecord(BaseModel):
    approver_id: str
    timestamp: datetime
    veritas_hash: str                   # The hash returned by Coreason-Veritas
```

### 5.3 The Master Protocol Definition

```python
class ProtocolDefinition(BaseModel):
    id: str
    title: str
    research_question: str              # Original natural language input

    # Design Layer (Mutable in DRAFT)
    pico_structure: Dict[str, PicoBlock]

    # Execution Layer (Generated on Approval)
    execution_strategies: List[ExecutableStrategy]

    # Governance Layer (Immutable Log)
    status: ProtocolStatus
    approval_history: Optional[ApprovalRecord]

    def render(self, format: str = "html") -> str:
        """Exports protocol for display."""
        pass

    def lock(self, user_id: str, veritas_client: Any) -> 'ProtocolDefinition':
        """Finalizes the protocol and registers with Veritas."""
        pass
```

---

## 6. Implementation Directives

1.  **State Machine:** The `ProtocolDefinition` is a State Machine. You must verify strict transitions (e.g., cannot move to APPROVED if PRESS validation fails or if `pico_structure` is empty).
2.  **Logic Robustness:** Use a library like `boolean.py` to construct query strings. Do not rely on simple string concatenation, which is prone to parenthesis errors. The `StrategyCompiler` should build an Abstract Syntax Tree (AST) first.
3.  **Visualization:** The `render(format="html")` method is critical. It must visualize the `TermOrigin`. Use conventions like **Bold** for User Input and *Italics* for System Expansion so the reviewer can instantly distinguish AI suggestions from human intent.
4.  **Audit Fidelity:** Never hard-delete a term when a human overrides it. Set `is_active=False` and require a reason string. This allows future auditors to see *what was considered and rejected*.

`[Codex Expansion] -> Draft Protocol -> [HITL Review UI] -> [Veritas Registration] -> ProtocolDefinition (Locked) -> [Coreason-Search]`
