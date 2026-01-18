import html
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

import pydantic_core
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from coreason_protocol.interfaces import VeritasClient


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

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("label")  # type: ignore[misc]
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class PicoBlock(BaseModel):  # type: ignore[misc]
    block_type: str  # "P", "I", "C", "O", "S"
    description: str  # "Elderly Patients"
    terms: List[OntologyTerm]  # The curated list of terms
    logic_operator: str = "OR"  # Logic intra-block

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("block_type")  # type: ignore[misc]
    @classmethod
    def validate_block_type(cls, v: str) -> str:
        if v not in ("P", "I", "C", "O", "S"):
            raise ValueError("block_type must be one of P, I, C, O, S")
        return v

    @field_validator("logic_operator")  # type: ignore[misc]
    @classmethod
    def validate_logic_operator(cls, v: str) -> str:
        if v not in ("AND", "OR", "NOT"):
            raise ValueError("logic_operator must be AND, OR, or NOT")
        return v


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

    @field_validator("veritas_hash")  # type: ignore[misc]
    @classmethod
    def validate_hash(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("veritas_hash cannot be empty")
        return v


class ProtocolDefinition(BaseModel):  # type: ignore[misc]
    id: str
    title: str
    research_question: str  # Original natural language input

    # Design Layer (Mutable in DRAFT)
    pico_structure: Dict[str, PicoBlock]

    # Execution Layer (Generated on Approval)
    execution_strategies: List[ExecutableStrategy] = Field(default_factory=list)

    # Governance Layer (Immutable Log)
    status: ProtocolStatus = ProtocolStatus.DRAFT
    approval_history: Optional[ApprovalRecord] = None

    model_config = ConfigDict(validate_assignment=True)

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
            # But wait, test expectations showed: '<b style="color: blue">Adults</b>'
            # My previous impl: <b style='color: blue; font-weight: bold;'>
            # I will try to match "color: blue" and maybe "font-weight: bold" if needed.
            # The test `test_render_html_basic` expects `<b style="color: blue">`.
            # I should output exactly that if possible, or update tests.
            # But the PRD asked for "Blue=User". It didn't mandate exact HTML string.
            # However, the existing tests are strict.
            # I will use `<b style="color: blue">` for User Input.
            # What about Human Injection? Test `test_render_human_injection` expects `<b style="color: blue">`.
            style = "color: blue"
            return f'<b style="{style}">{label}</b>'

        if term.origin == TermOrigin.SYSTEM_EXPANSION:
            # Grey, Italics
            style = "color: grey"
            return f'<i style="{style}">{label}</i>'

        # Fallback (should not happen given Enum)
        return label  # pragma: no cover

    def lock(self, user_id: str, veritas_client: "VeritasClient") -> "ProtocolDefinition":
        """Finalizes the protocol and registers with Veritas."""
        if self.status in (ProtocolStatus.APPROVED, ProtocolStatus.EXECUTED):
            # Matches existing test expectation
            raise ValueError("Cannot lock a protocol that is already APPROVED or EXECUTED")

        if not self.pico_structure:
            # Matches existing test expectation
            raise ValueError("Cannot lock a protocol with an empty PICO structure")

        if self.status != ProtocolStatus.DRAFT:
            # Fallback for other states if any
            raise ValueError(f"Cannot lock protocol in state: {self.status}")

        # Register with Veritas
        protocol_hash = veritas_client.register_protocol(self.model_dump(mode="json"))

        # Create approval record
        self.approval_history = ApprovalRecord(
            approver_id=user_id, timestamp=datetime.now(timezone.utc), veritas_hash=protocol_hash
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

    def compile(self, target: str = "PUBMED") -> List[ExecutableStrategy]:
        """
        Compiles the protocol into executable search strategies.
        This is a convenience wrapper around StrategyCompiler.

        Args:
            target: The target execution engine (default: "PUBMED").

        Returns:
            List[ExecutableStrategy]: The compiled strategies. Also updates self.execution_strategies.
        """
        from coreason_protocol.compiler import StrategyCompiler

        compiler = StrategyCompiler()
        strategy = compiler.compile(self, target=target)

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
