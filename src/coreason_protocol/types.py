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

from pydantic import BaseModel, Field


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
    status: ProtocolStatus = ProtocolStatus.DRAFT
    approval_history: Optional[ApprovalRecord] = None

    def render(self, format: str = "html") -> str:
        """Exports protocol for display."""
        # Placeholder for AUC 5
        return ""

    def lock(self, user_id: str, veritas_client: Any) -> "ProtocolDefinition":
        """Finalizes the protocol and registers with Veritas."""
        # Placeholder for AUC 2
        return self
