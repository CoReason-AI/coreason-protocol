import html
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

import pydantic_core
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from coreason_protocol.interfaces import VeritasClientProtocol


class TermOrigin(str, Enum):
    USER_INPUT = "USER_INPUT"  # The user typed this
    SYSTEM_EXPANSION = "SYSTEM_EXPANSION"  # Codex added this (Ontology child)
    HUMAN_INJECTION = "HUMAN_INJECTION"  # Reviewer added this manually


class OntologyTerm(BaseModel):  # type: ignore[misc]
    id: str  # UUID
    label: str  # "Myocardial Infarction"
    vocab_source: str  # "MeSH"
    code: str  # "D009203"
    origin: TermOrigin
    is_active: bool = True  # False if soft-deleted by human
    override_reason: Optional[str] = None  # e.g., "Term captures non-human studies"


class PicoBlock(BaseModel):  # type: ignore[misc]
    block_type: str  # "P", "I", "C", "O", "S"
    description: str  # "Elderly Patients"
    terms: List[OntologyTerm]  # The curated list of terms
    logic_operator: str = "OR"  # Logic intra-block


class ProtocolStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"  # Locked & Registered
    EXECUTED = "EXECUTED"


class ExecutableStrategy(BaseModel):  # type: ignore[misc]
    target: str  # "PUBMED", "LANCEDB"
    query_string: str  # The compiled code string
    validation_status: str  # "PRESS_PASSED" or "WARNINGS"


class ApprovalRecord(BaseModel):  # type: ignore[misc]
    approver_id: str
    timestamp: datetime
    veritas_hash: str  # The hash returned by Coreason-Veritas


class ProtocolDefinition(BaseModel):  # type: ignore[misc]
    id: str
    title: str
    research_question: str  # Original natural language input

    # Design Layer (Mutable in DRAFT)
    pico_structure: Dict[str, PicoBlock]

    # Execution Layer (Generated on Approval)
    execution_strategies: List[ExecutableStrategy] = Field(default_factory=list)

    # Governance Layer (Immutable Log)
    status: ProtocolStatus
    approval_history: Optional[ApprovalRecord] = None

    @field_validator("pico_structure")  # type: ignore[misc]
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
            HTML string representation of the protocol.

        Raises:
            ValueError: If format is not 'html'.
        """
        if format != "html":
            raise ValueError(f"Unsupported format: {format}")

        output = []

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
            output.append(f"<h2>{block_type}: {html.escape(block.description)}</h2>")
            output.append("<ul>")

            for term in block.terms:
                term_html = self._render_term(term)
                output.append(f"<li>{term_html}</li>")

            output.append("</ul>")
            output.append("</div>")

        return "\n".join(output)

    def _render_term(self, term: OntologyTerm) -> str:
        """Helper to render a single term with styles."""
        label = html.escape(term.label)

        if not term.is_active:
            # Red, strikethrough, tooltip
            style = "color: red; text-decoration: line-through;"
            reason = html.escape(term.override_reason or "")
            return f"<span style='{style}' title='{reason}'>{label}</span>"

        if term.origin in (TermOrigin.USER_INPUT, TermOrigin.HUMAN_INJECTION):
            # Blue, Bold
            style = "color: blue; font-weight: bold;"
            return f"<b style='{style}'>{label}</b>"

        if term.origin == TermOrigin.SYSTEM_EXPANSION:
            # Grey, Italics
            style = "color: grey; font-style: italic;"
            return f"<i style='{style}'>{label}</i>"

        # Fallback (should not happen given Enum)
        return label  # pragma: no cover

    def lock(self, user_id: str, veritas_client: "VeritasClientProtocol") -> "ProtocolDefinition":
        """Finalizes the protocol and registers with Veritas."""
        if self.status != ProtocolStatus.DRAFT:
            raise ValueError(f"Cannot lock protocol in state: {self.status}")

        if not self.pico_structure:
            raise ValueError("Cannot lock protocol with empty PICO structure")

        # Register with Veritas
        protocol_hash = veritas_client.register_protocol(self.model_dump(mode="json"))

        # Create approval record
        self.approval_history = ApprovalRecord(
            approver_id=user_id, timestamp=datetime.now(timezone.utc), veritas_hash=protocol_hash
        )

        # Update status
        self.status = ProtocolStatus.APPROVED

        return self

    def override_term(self, block_type: str, term_id: str, reason: str) -> None:
        """
        Soft-deletes a term from the protocol.

        Args:
            block_type: The PICO block type (P, I, C, O, S).
            term_id: The UUID of the term.
            reason: The reason for overriding.

        Raises:
            RuntimeError: If protocol is not in DRAFT or PENDING_REVIEW.
            ValueError: If reason is empty or term not found.
        """
        if self.status not in (ProtocolStatus.DRAFT, ProtocolStatus.PENDING_REVIEW):
            raise RuntimeError(f"Cannot modify protocol in state: {self.status}")

        if not reason or not reason.strip():
            raise ValueError("Override reason must be provided")

        if block_type not in self.pico_structure:
            raise ValueError(f"Block type '{block_type}' not found")

        block = self.pico_structure[block_type]
        for term in block.terms:
            if term.id == term_id:
                term.is_active = False
                term.override_reason = reason
                return

        raise ValueError(f"Term '{term_id}' not found in block '{block_type}'")

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
        if self.status not in (ProtocolStatus.DRAFT, ProtocolStatus.PENDING_REVIEW):
            raise RuntimeError(f"Cannot modify protocol in state: {self.status}")

        # Enforce uniqueness globally
        for blk in self.pico_structure.values():
            for t in blk.terms:
                if t.id == term.id:
                    if t.origin == TermOrigin.HUMAN_INJECTION and block_type == blk.block_type:
                        # Idempotency: if exact same injection exists in same block, ignore
                        return
                    raise ValueError(f"Term ID '{term.id}' already exists in block '{blk.block_type}'")

        # Force origin
        term.origin = TermOrigin.HUMAN_INJECTION

        # Add to block (create if missing)
        if block_type not in self.pico_structure:
            self.pico_structure[block_type] = PicoBlock(
                block_type=block_type, description=f"Manual Injection for {block_type}", terms=[]
            )

        self.pico_structure[block_type].terms.append(term)
