import html
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

import pydantic_core
from coreason_identity.models import UserContext
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from coreason_protocol.interfaces import VeritasClient


class TermOrigin(str, Enum):
    """
    Origin of a term in the protocol.

    Attributes:
        USER_INPUT: The term was explicitly provided by the user.
        SYSTEM_EXPANSION: The term was added by the system via ontology expansion.
        HUMAN_INJECTION: The term was manually injected by a human reviewer.
    """

    USER_INPUT = "USER_INPUT"
    SYSTEM_EXPANSION = "SYSTEM_EXPANSION"
    HUMAN_INJECTION = "HUMAN_INJECTION"


class Target(str, Enum):
    """
    Supported execution targets for the protocol.

    Attributes:
        PUBMED: PubMed/MEDLINE database.
        LANCEDB: LanceDB vector database.
        GRAPH: Graph database (e.g., Neo4j).
    """

    PUBMED = "PUBMED"
    LANCEDB = "LANCEDB"
    GRAPH = "GRAPH"


class VocabSource(str, Enum):
    """
    Controlled vocabulary sources.

    Attributes:
        MESH: Medical Subject Headings.
    """

    MESH = "MeSH"


class OntologyTerm(BaseModel):
    """
    Represents a single term from a controlled vocabulary.

    Attributes:
        id: Unique identifier (UUID).
        label: Human-readable label (e.g., "Myocardial Infarction").
        vocab_source: Source vocabulary (e.g., "MeSH").
        code: Concept code (e.g., "D009203").
        origin: How this term was added to the protocol.
        is_active: Whether the term is active or soft-deleted.
        override_reason: Reason for soft-deletion, if applicable.
    """

    id: str
    label: str
    vocab_source: str
    code: str
    origin: TermOrigin
    is_active: bool = True
    override_reason: Optional[str] = None

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("label")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class PicoBlock(BaseModel):
    """
    Represents a PICO block (Population, Intervention, Comparator, Outcome, Study Design).

    Attributes:
        block_type: The type of block (P, I, C, O, S).
        description: A human-readable description of the block's intent.
        terms: List of ontology terms in this block.
        logic_operator: Intra-block logic operator (AND, OR, NOT).
    """

    block_type: str
    description: str
    terms: List[OntologyTerm]
    logic_operator: str = "OR"

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("block_type")
    @classmethod
    def validate_block_type(cls, v: str) -> str:
        if v not in ("P", "I", "C", "O", "S"):
            raise ValueError("block_type must be one of P, I, C, O, S")
        return v

    @field_validator("logic_operator")
    @classmethod
    def validate_logic_operator(cls, v: str) -> str:
        if v not in ("AND", "OR", "NOT"):
            raise ValueError("logic_operator must be AND, OR, or NOT")
        return v


class ProtocolStatus(str, Enum):
    """
    Lifecycle status of a protocol.

    Attributes:
        DRAFT: Initial design phase, mutable.
        PENDING_REVIEW: Submitted for review, immutable except for reviewer actions.
        APPROVED: Finalized, locked, and registered with Veritas.
        EXECUTED: Has been run against a target.
    """

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"


class ExecutableStrategy(BaseModel):
    """
    A compiled search strategy for a specific target.

    Attributes:
        target: The target execution engine.
        query_string: The compiled query code.
        validation_status: Status of automated validation (e.g., PRESS checks).
    """

    target: str
    query_string: str
    validation_status: str


class ApprovalRecord(BaseModel):
    """
    Record of a human sign-off event.

    Attributes:
        approver_id: ID of the user who approved the protocol.
        timestamp: When the approval occurred.
        veritas_hash: The immutable hash returned by the audit system.
    """

    approver_id: str
    timestamp: datetime
    veritas_hash: str

    @field_validator("veritas_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("veritas_hash cannot be empty")
        return v


class ProtocolDefinition(BaseModel):
    """
    The master definition of a search protocol.
    Acts as the "Design Plane" state machine.

    Attributes:
        id: Unique identifier for the protocol.
        title: Human-readable title.
        research_question: The original natural language intent.
        pico_structure: Dictionary of PICO blocks defining the search logic.
        execution_strategies: List of compiled strategies for different targets.
        status: Current lifecycle state.
        approval_history: Record of final approval and registration.
    """

    id: str
    title: str
    research_question: str

    # Design Layer (Mutable in DRAFT)
    pico_structure: Dict[str, PicoBlock]

    # Execution Layer (Generated on Approval)
    execution_strategies: List[ExecutableStrategy] = Field(default_factory=list)

    # Governance Layer (Immutable Log)
    status: ProtocolStatus = ProtocolStatus.DRAFT
    approval_history: Optional[ApprovalRecord] = None

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("pico_structure")
    @classmethod
    def validate_pico_structure(cls, v: Dict[str, PicoBlock]) -> Dict[str, PicoBlock]:
        for key, block in v.items():
            if key != block.block_type:
                raise pydantic_core.PydanticCustomError(
                    "value_error",
                    f"Key mismatch in pico_structure: Key '{key}' does not match block_type '{block.block_type}'",
                )
        return v

    def render(self, format: str = "html") -> str:
        """Exports protocol for display.

        Args:
            format: Output format, currently only 'html' is supported.

        Returns:
            str: HTML string representation of the protocol.

        Raises:
            ValueError: If format is not 'html'.
        """
        if format != "html":
            raise ValueError(f"Unsupported format: {format}")

        output = []

        # Wrapper
        output.append(f'<div id="{html.escape(self.id)}" class="protocol">')

        # Header
        output.append(f"<h1>Protocol: {html.escape(self.title)}</h1>")
        output.append(f"<p><strong>ID:</strong> {html.escape(self.id)}</p>")
        output.append(f"<p><strong>Question:</strong> {html.escape(self.research_question)}</p>")
        output.append("<hr>")

        # PICO Structure
        # Order: P, I, C, O, S (if present)
        order = ["P", "I", "C", "O", "S"]

        for block_type in order:
            if block_type not in self.pico_structure:
                continue

            block = self.pico_structure[block_type]
            output.append(f"<div class='pico-block' id='block-{block_type}'>")
            # Format: Description (Type)
            output.append(f"<h2>{html.escape(block.description)} ({block_type})</h2>")
            output.append("<ul>")

            for term in block.terms:
                term_html = self._render_term(term)
                output.append(f"<li>{term_html}</li>")

            output.append("</ul>")
            output.append("</div>")

        output.append("</div>")

        return "\n".join(output)

    def _render_term(self, term: OntologyTerm) -> str:
        """Helper to render a single term with styles."""
        label = html.escape(term.label)

        if not term.is_active:
            # Red, strikethrough, tooltip
            style = "color: red; text-decoration: line-through;"
            # Escape quotes for attribute safety
            reason_raw = term.override_reason or ""
            reason_attr = ""
            if reason_raw:
                reason_escaped = html.escape(reason_raw, quote=True)
                # Matches existing test expectation: title="Reason: ..."
                reason_attr = f' title="Reason: {reason_escaped}"'

            return f"<span style='{style}'{reason_attr}>{label}</span>"

        if term.origin in (TermOrigin.USER_INPUT, TermOrigin.HUMAN_INJECTION):
            # Blue, Bold
            # Updated to double quotes for style attribute to match test expectations
            style = "color: blue"
            return f'<b style="{style}">{label}</b>'

        if term.origin == TermOrigin.SYSTEM_EXPANSION:
            # Grey, Italics
            style = "color: grey"
            return f'<i style="{style}">{label}</i>'

        # Fallback (should not happen given Enum)
        return label  # pragma: no cover

    def lock(self, context: UserContext, veritas_client: "VeritasClient") -> "ProtocolDefinition":
        """Finalizes the protocol and registers with Veritas.

        Args:
            context: User identity context.
            veritas_client: Client for the Veritas audit system.

        Returns:
            ProtocolDefinition: The locked protocol instance (self).

        Raises:
            ValueError: If protocol is already approved/executed or validation fails.
        """
        if self.status in (ProtocolStatus.APPROVED, ProtocolStatus.EXECUTED):
            # Matches existing test expectation
            raise ValueError("Cannot lock a protocol that is already APPROVED or EXECUTED")

        if self.status != ProtocolStatus.DRAFT:
            # Fallback for other states if any
            raise ValueError(f"Cannot lock protocol in state: {self.status}")

        # Validate structural integrity (PRESS-based)
        from coreason_protocol.validator import ProtocolValidator

        ProtocolValidator.validate(self)

        # Register with Veritas
        protocol_hash = veritas_client.register_protocol(self.model_dump(mode="json"))

        # Create approval record
        self.approval_history = ApprovalRecord(
            approver_id=context.user_id,
            timestamp=datetime.now(timezone.utc),
            veritas_hash=protocol_hash,
        )

        # Update status
        self.status = ProtocolStatus.APPROVED

        return self

    def override_term(self, term_id: str, reason: str) -> None:
        """
        Soft-deletes a term from the protocol.

        Args:
            term_id: The UUID of the term.
            reason: The reason for overriding.

        Raises:
            RuntimeError: If protocol is not in DRAFT or PENDING_REVIEW.
            ValueError: If reason is empty or term not found.
        """
        if self.status == ProtocolStatus.APPROVED:
            raise RuntimeError("Cannot modify protocol in APPROVED state")

        if self.status == ProtocolStatus.EXECUTED:
            raise RuntimeError("Cannot modify protocol in EXECUTED state")

        if self.status not in (ProtocolStatus.DRAFT, ProtocolStatus.PENDING_REVIEW):
            raise RuntimeError(f"Cannot modify protocol in state: {self.status}")  # pragma: no cover

        if not reason or not reason.strip():
            raise ValueError("Override reason cannot be empty")  # Matches existing test

        # Iterate all blocks to find the term
        term_found = False
        for block in self.pico_structure.values():
            for term in block.terms:
                if term.id == term_id:
                    term.is_active = False
                    term.override_reason = reason
                    term_found = True
                    return  # Term ID is globally unique, so we can stop

        if not term_found:
            raise ValueError(f"Term ID '{term_id}' not found in protocol")  # Matches existing test

    def inject_term(self, block_type: str, term: OntologyTerm) -> None:
        """
        Injects a new term into the protocol.

        Args:
            block_type: The PICO block type.
            term: The term object to inject.

        Raises:
            RuntimeError: If protocol is not mutable.
            ValueError: If term ID is not globally unique.
        """
        if self.status == ProtocolStatus.APPROVED:
            raise RuntimeError("Cannot modify protocol in APPROVED state")

        if self.status == ProtocolStatus.EXECUTED:
            raise RuntimeError("Cannot modify protocol in EXECUTED state")

        if self.status not in (ProtocolStatus.DRAFT, ProtocolStatus.PENDING_REVIEW):
            raise RuntimeError(f"Cannot modify protocol in state: {self.status}")  # pragma: no cover

        # Enforce uniqueness globally
        for blk in self.pico_structure.values():
            for t in blk.terms:
                if t.id == term.id:
                    if block_type == blk.block_type:
                        # Idempotency: if exact same injection exists in same block, ignore
                        # This applies even if origin differs (e.g. attempting to inject an existing System Expansion)
                        return
                    raise ValueError(f"Term ID '{term.id}' already exists in block '{blk.block_type}'")

        # Force origin
        term.origin = TermOrigin.HUMAN_INJECTION

        # Add to block (create if missing)
        if block_type not in self.pico_structure:
            self.pico_structure[block_type] = PicoBlock(
                block_type=block_type, description=block_type, terms=[]
            )  # Updated description to match "I"

        self.pico_structure[block_type].terms.append(term)

    def compile(self, context: UserContext, target: str = "PUBMED") -> List[ExecutableStrategy]:
        """
        Compiles the protocol into executable search strategies.
        This is a convenience wrapper around StrategyCompiler.

        Args:
            context: User identity context.
            target: The target execution engine (default: "PUBMED").

        Returns:
            List[ExecutableStrategy]: The compiled strategies. Also updates self.execution_strategies.
        """
        from coreason_protocol.compiler import StrategyCompiler

        compiler = StrategyCompiler()
        strategy = compiler.compile(self, context=context, target=target)

        # Idempotency: Update existing strategy for the target if present
        updated = False
        for i, existing in enumerate(self.execution_strategies):
            if existing.target == target:
                self.execution_strategies[i] = strategy
                updated = True
                break

        if not updated:
            self.execution_strategies.append(strategy)

        return [strategy]
