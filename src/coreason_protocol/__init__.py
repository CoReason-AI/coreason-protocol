# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

"""
coreason-protocol
"""

__version__ = "0.1.0"
__author__ = "Gowtham A Rao"
__email__ = "gowtham.rao@coreason.ai"

from .compiler import StrategyCompiler
from .interfaces import VeritasClient
from .types import (
    ApprovalRecord,
    ExecutableStrategy,
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    ProtocolStatus,
    TermOrigin,
)

__all__ = [
    "ApprovalRecord",
    "ExecutableStrategy",
    "OntologyTerm",
    "PicoBlock",
    "ProtocolDefinition",
    "ProtocolStatus",
    "StrategyCompiler",
    "TermOrigin",
    "VeritasClient",
]
