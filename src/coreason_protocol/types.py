# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

import html
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from coreason_protocol.interfaces import VeritasClient


class TermOrigin(str, Enum):
    """Origin of a term in the protocol."""

    USER_INPUT = "USER_INPUT"  # The user typed this
    SYSTEM_EXPANSION = "SYSTEM_EXPANSION"  # Codex added this (Ontology child)
    HUMAN_INJECTION = "HUMAN_INJECTION"  # Reviewer added this manually


class OntologyTerm(BaseModel):  # type: ignore[misc]
    """A term from a controlled vocabulary."""

    model_config = ConfigDict(validate_assignment=True)

    id: str  # UUID
    label: str  # "Myocardial Infarction"
    vocab_source: str  # "MeSH"
    code: str  # "D009203"
    origin: TermOrigin
    is_active: bool = True  # False if soft-deleted by human
    override_reason: Optional[str] = None  # e.g., "Term captures non-human studies"

    @field_validator("id", "label", "vocab_source", "code")  # type: ignore[misc]
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v


class PicoBlock(BaseModel):  # type: ignore[misc]
    """A block of the PICO search strategy."""

    model_config = ConfigDict(validate_assignment=True)

    block_type: str  # "P", "I", "C", "O", "S"
    description: str  # "Elderly Patients"
    terms: List[OntologyTerm]  # The curated list of terms
    logic_operator: str = "OR"  # Logic intra-block

    @field_validator("block_type")  # type: ignore[misc]
    @classmethod
    def check_block_type(cls, v: str) -> str:
        if v not in {"P", "I", "C", "O", "S"}:
            raise ValueError("block_type must be one of P, I, C, O, S")
        return v

    @field_validator("logic_operator")  # type: ignore[misc]
    @classmethod
    def check_logic_operator(cls, v: str) -> str:
        if v not in {"AND", "OR", "NOT"}:
            raise ValueError("logic_operator must be AND, OR, or NOT")
        return v

    @field_validator("description")  # type: ignore[misc]
    @classmethod
    def check_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("description cannot be empty or whitespace")
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
    def check_hash_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("veritas_hash cannot be empty or whitespace")
        return v


class ProtocolDefinition(BaseModel):  # type: ignore[misc]
    model_config = ConfigDict(validate_assignment=True)

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

    @field_validator("pico_structure")  # type: ignore[misc]
    @classmethod
    def validate_pico_structure(cls, v: Dict[str, PicoBlock]) -> Dict[str, PicoBlock]:
        """Ensure that keys match the block_type of the PicoBlock."""
        for key, block in v.items():
            if key != block.block_type:
                raise ValueError(
                    f"Key mismatch in pico_structure: Key '{key}' does not match block_type '{block.block_type}'"
                )
        return v

    def render(self, format: str = "html") -> str:
        """Exports protocol for display."""
        if format != "html":
            raise ValueError(f"Unsupported format: {format}")

        output = []
        output.append(f'<div class="protocol" id="{html.escape(self.id)}">')
        output.append(f"<h2>{html.escape(self.title)}</h2>")
        output.append(f"<p>{html.escape(self.research_question)}</p>")

        for block in self.pico_structure.values():
            output.append('<div class="pico-block">')
            output.append(f"<h3>{html.escape(block.description)} ({html.escape(block.block_type)})</h3>")
            output.append("<ul>")

            for term in block.terms:
                escaped_label = html.escape(term.label)
                style_parts = []
                attributes = ""

                # Determine base style and tag based on origin
                if term.origin in {TermOrigin.USER_INPUT, TermOrigin.HUMAN_INJECTION}:
                    tag = "b"
                    color = "blue"
                else:  # SYSTEM_EXPANSION
                    tag = "i"
                    color = "grey"

                # Handle deleted/inactive terms
                if not term.is_active:
                    color = "red"
                    style_parts.append("text-decoration: line-through")
                    if term.override_reason:
                        attributes = f' title="Reason: {html.escape(term.override_reason)}"'

                style_parts.insert(0, f"color: {color}")
                style_attr = f' style="{"; ".join(style_parts)}"'

                output.append(f"<li><{tag}{style_attr}{attributes}>{escaped_label}</{tag}></li>")

            output.append("</ul>")
            output.append("</div>")

        output.append("</div>")
        return "\n".join(output)

    def lock(self, user_id: str, veritas_client: VeritasClient) -> "ProtocolDefinition":
        """Finalizes the protocol and registers with Veritas."""
        if self.status in {ProtocolStatus.APPROVED, ProtocolStatus.EXECUTED}:
            raise ValueError("Cannot lock a protocol that is already APPROVED or EXECUTED")

        if not self.pico_structure:
            raise ValueError("Cannot lock a protocol with an empty PICO structure")

        # Create approval record
        timestamp = datetime.now(timezone.utc)
        payload = self.model_dump()
        veritas_hash = veritas_client.register_protocol(payload)

        self.approval_history = ApprovalRecord(
            approver_id=user_id,
            timestamp=timestamp,
            veritas_hash=veritas_hash,
        )
        self.status = ProtocolStatus.APPROVED

        return self

    def override_term(self, term_id: str, reason: str) -> None:
        """Soft-deletes a synonym suggested by AI."""
        if self.status not in {ProtocolStatus.DRAFT, ProtocolStatus.PENDING_REVIEW}:
            raise RuntimeError(f"Cannot modify protocol in {self.status.value} state")

        if not reason or not reason.strip():
            raise ValueError("Override reason cannot be empty")

        for block in self.pico_structure.values():
            for term in block.terms:
                if term.id == term_id:
                    term.is_active = False
                    term.override_reason = reason
                    return

        raise ValueError(f"Term ID '{term_id}' not found in protocol")

    def inject_term(self, block_type: str, term: OntologyTerm) -> None:
        """Adds a manual keyword missed by the ontology."""
        if self.status not in {ProtocolStatus.DRAFT, ProtocolStatus.PENDING_REVIEW}:
            raise RuntimeError(f"Cannot modify protocol in {self.status.value} state")

        # Force origin to HUMAN_INJECTION
        term.origin = TermOrigin.HUMAN_INJECTION

        # Check for global uniqueness or idempotency
        for block in self.pico_structure.values():
            for existing_term in block.terms:
                if existing_term.id == term.id:
                    if block.block_type == block_type:
                        # Idempotent: exists in target block, do nothing
                        return
                    else:
                        # Conflict: exists in another block
                        raise ValueError(f"Term ID '{term.id}' already exists in block '{block.block_type}'")

        # Get or create block
        if block_type in self.pico_structure:
            block = self.pico_structure[block_type]
        else:
            block = PicoBlock(
                block_type=block_type,
                description=block_type,  # Default description
                terms=[],
            )
            self.pico_structure[block_type] = block

        block.terms.append(term)
