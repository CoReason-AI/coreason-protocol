# The Architecture and Utility of coreason-protocol

## 1. The Philosophy (The Why)

In high-stakes research—such as clinical systematic reviews or regulatory submissions—the search strategy is the foundation of evidence. Yet, traditionally, this foundation has been a "black box": an opaque string of boolean logic constructed by a human librarian, often prone to error and difficult to audit.

**coreason-protocol** was built to solve this opacity. It operates on the philosophy that **"The Protocol is the Law."**

The package transforms the creation of a search strategy from a manual art into a **Rigorous, Audited, and Executable Engineering Workflow**. It is not merely a tool for retrieving documents (RAG); it is a governance engine. It enforces a strict separation of concerns:
*   **Design:** An AI agent proposes a PICO structure (Population, Intervention, Comparator, Outcome).
*   **Validation:** The system enforces PRESS (Peer Review of Electronic Search Strategies) guidelines before a human ever sees it.
*   **Governance:** A human expert must explicitly review, override, or inject terms.
*   **Registration:** The final protocol is hashed and locked, ensuring that the strategy executed is exactly the strategy approved.

By treating the search protocol as a version-controlled, immutable software artifact, `coreason-protocol` brings software engineering rigor to evidence synthesis.

## 2. Under the Hood (The Dependencies & Logic)

The architecture of `coreason-protocol` is designed for correctness, traceability, and "audit fidelity."

*   **`pydantic` (Data Integrity):** The core of the system is the `ProtocolDefinition` model. Unlike simple dictionaries, these "rich models" enforce business logic at the type level. For instance, the system refuses to transition to an `APPROVED` state if the PICO structure is structurally invalid, and it prevents modification of `APPROVED` protocols entirely.
*   **`boolean.py` (Logic Robustness):** Constructing complex search queries via string concatenation is fragile. This package uses `boolean.py` to build an Abstract Syntax Tree (AST) of the query logic. This allows the `StrategyCompiler` to safely manipulate boolean operators (AND, OR, NOT) and render them correctly for different targets (PubMed, Ovid) without parenthesis errors.
*   **`loguru` (Observability):** Every compilation step and state transition is logged, providing a breadcrumb trail for debugging.
*   **State Machine Logic:** The `ProtocolDefinition` acts as a state machine. Methods like `lock()` validation and state transitions are atomic. The `StrategyCompiler` employs the Strategy Pattern to support polyglot outputs—generating Mesh-tagged strings for `PubMed`, vector embeddings for `LanceDB`, and Cypher queries for `Graph` databases from the same source of truth.

## 3. In Practice (The How)

Here is how `coreason-protocol` orchestrates the lifecycle of a search strategy, from a raw idea to a locked, executable artifact.

### Example 1: Creating a Draft and Designing PICO

The entry point is the `ProtocolDefinition`. We start by defining our research question and populating the PICO blocks.

```python
from coreason_protocol.types import ProtocolDefinition, PicoBlock, OntologyTerm, TermOrigin

# 1. Initialize a Draft Protocol
protocol = ProtocolDefinition(
    id="prot-123",
    title="Statin Use in Elderly",
    research_question="Does statin use reduce mortality in patients over 80?",
    pico_structure={}
)

# 2. Add an 'Intervention' Block (e.g., populated by AI or User)
statin_term = OntologyTerm(
    id="term-001",
    label="Hydroxymethylglutaryl-CoA Reductase Inhibitors",
    vocab_source="MeSH",
    code="D019161",
    origin=TermOrigin.SYSTEM_EXPANSION
)

protocol.pico_structure["I"] = PicoBlock(
    block_type="I",
    description="Statins",
    terms=[statin_term],
    logic_operator="OR"
)
```

### Example 2: Human-in-the-Loop Governance

A key feature is **audit fidelity**. If a human expert disagrees with an AI suggestion, we don't just delete it. We "soft-delete" it with a reason, preserving the decision history.

```python
# 3. Human Expert Overrides a Term (Soft Delete)
protocol.override_term(
    term_id="term-001",
    reason="Too broad; focusing on Atorvastatin specifically."
)

# 4. Human Injects a Specific Term
new_term = OntologyTerm(
    id="term-002",
    label="Atorvastatin",
    vocab_source="MeSH",
    code="C000591290",
    origin=TermOrigin.HUMAN_INJECTION
)

protocol.inject_term(block_type="I", term=new_term)
```

### Example 3: Locking and Compiling

Once the design is finalized, we lock the protocol (registering it with the Veritas audit system) and compile it into executable code for PubMed.

```python
from coreason_protocol.types import ProtocolStatus

# Mock Veritas Client for demonstration
class MockVeritas:
    def register_protocol(self, data):
        return "sha256:8f43..."

# 5. Lock and Approve (State Transition)
# This validates the structure (PRESS guidelines) and freezes the object.
protocol.lock(user_id="user-456", veritas_client=MockVeritas())

print(f"Status: {protocol.status}") # Output: ProtocolStatus.APPROVED

# 6. Compile for Execution
# The Compiler translates our PICO object into a PubMed-syntax query string.
strategies = protocol.compile(target="PUBMED")

print(strategies[0].query_string)
# Output: "Atorvastatin"[TiAb]
# Note: The overridden term is excluded automatically.
```
