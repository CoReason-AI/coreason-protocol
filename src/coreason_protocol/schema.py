# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


class TermOrigin(str, Enum):
    """Origin of a term in the protocol."""

    USER_INPUT = "USER_INPUT"  # The user typed this
    SYSTEM_EXPANSION = "SYSTEM_EXPANSION"  # Codex added this (Ontology child)
    HUMAN_INJECTION = "HUMAN_INJECTION"  # Reviewer added this manually


class OntologyTerm(BaseModel):  # type: ignore[misc]
    """A term from a controlled vocabulary."""

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
    """Status of the protocol in the governance lifecycle."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"  # Locked & Registered
    EXECUTED = "EXECUTED"


class ExecutableStrategy(BaseModel):  # type: ignore[misc]
    """A compiled search strategy for a specific target."""

    target: str  # "PUBMED", "LANCEDB"
    query_string: str  # The compiled code string
    validation_status: str  # "PRESS_PASSED" or "WARNINGS"

    @field_validator("target", "query_string", "validation_status")  # type: ignore[misc]
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v


class ApprovalRecord(BaseModel):  # type: ignore[misc]
    """Record of a human sign-off."""

    approver_id: str
    timestamp: datetime
    veritas_hash: str  # The hash returned by Coreason-Veritas

    @field_validator("approver_id", "veritas_hash")  # type: ignore[misc]
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v


class ProtocolDefinition(BaseModel):  # type: ignore[misc]
    """The Master Protocol Definition."""

    id: str
    title: str
    research_question: str  # Original natural language input

    # Design Layer (Mutable in DRAFT)
    pico_structure: Dict[str, PicoBlock]

    # Execution Layer (Generated on Approval)
    execution_strategies: List[ExecutableStrategy]

    # Governance Layer (Immutable Log)
    status: ProtocolStatus
    approval_history: Optional[ApprovalRecord] = None

    @field_validator("id", "title", "research_question")  # type: ignore[misc]
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v

    def render(self, format: str = "html") -> str:
        """Exports protocol for display."""
        raise NotImplementedError("render() is not yet implemented")

    def lock(self, user_id: str, veritas_client: Any) -> "ProtocolDefinition":
        """Finalizes the protocol and registers with Veritas."""
        raise NotImplementedError("lock() is not yet implemented")
