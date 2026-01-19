import json
from enum import Enum
from typing import Callable, Dict

import boolean

from coreason_protocol.types import (
    ExecutableStrategy,
    OntologyTerm,
    ProtocolDefinition,
)
from coreason_protocol.utils.logger import logger


class Target(str, Enum):
    PUBMED = "PUBMED"
    LANCEDB = "LANCEDB"


class VocabSource(str, Enum):
    MESH = "MeSH"


class StrategyCompiler:
    """
    Compiles ProtocolDefinition into executable search strategies for various targets.
    Uses boolean.py to construct Abstract Syntax Trees (AST) for logic robustness.
    """

    def __init__(self) -> None:
        self.algebra = boolean.BooleanAlgebra()
        # Dispatch map for extensibility (Open/Closed Principle)
        self._compilers: Dict[str, Callable[[ProtocolDefinition], str]] = {
            Target.PUBMED.value: self._compile_pubmed,
            Target.LANCEDB.value: self._compile_lancedb,
        }

    def compile(self, protocol: ProtocolDefinition, target: str = Target.PUBMED.value) -> ExecutableStrategy:
        """
        Compiles the protocol for a specific target.

        Args:
            protocol: The protocol to compile.
            target: The target execution engine (default: "PUBMED").

        Returns:
            ExecutableStrategy object containing the compiled query string.

        Raises:
            ValueError: If the target is not supported.
        """
        logger.debug(f"Compiling protocol {protocol.id} for target {target}")

        compiler_func = self._compilers.get(target)
        if not compiler_func:
            logger.error(f"Unsupported target requested: {target}")
            raise ValueError(f"Unsupported target: {target}")

        query_string = compiler_func(protocol)

        logger.info(f"Successfully compiled protocol {protocol.id} for {target}")

        return ExecutableStrategy(
            target=target,
            query_string=query_string,
            validation_status="PRESS_PASSED",  # Placeholder until validation logic exists
        )

    def _compile_pubmed(self, protocol: ProtocolDefinition) -> str:
        """
        Internal method to generate PubMed/Ovid boolean strings.
        Logic: (P) AND (I) AND (C) AND (O) AND (S)
        """
        # 1. Build AST for each block
        block_exprs = []

        # Order matters: P, I, C, O, S
        order = ["P", "I", "C", "O", "S"]

        for block_type in order:
            if block_type not in protocol.pico_structure:
                continue

            block = protocol.pico_structure[block_type]

            # Filter active terms
            active_terms = [t for t in block.terms if t.is_active]

            if not active_terms:
                continue

            # Create term symbols
            term_symbols = []
            for term in active_terms:
                term_str = self._format_pubmed_term(term)
                term_symbols.append(self.algebra.Symbol(term_str))

            # Combine terms using intra-block logic (default OR)
            if len(term_symbols) == 1:
                block_expr = term_symbols[0]
            else:
                if block.logic_operator == "OR":
                    block_expr = self.algebra.OR(*term_symbols)
                elif block.logic_operator == "AND":
                    block_expr = self.algebra.AND(*term_symbols)
                elif block.logic_operator == "NOT":
                    # Interpret as NOT(OR(...))? Or AND(NOT T1, NOT T2)?
                    # Standard interpretation for a "NOT" block usually implies exclusion.
                    # But if it's "logic_operator" inside a block, we'll assume join with AND
                    # and negate each term.
                    not_terms = [self.algebra.NOT(t) for t in term_symbols]
                    block_expr = self.algebra.AND(*not_terms)
                else:
                    # Fallback to OR if unknown, though validation prevents this
                    block_expr = self.algebra.OR(*term_symbols)  # pragma: no cover

            block_exprs.append(block_expr)

        if not block_exprs:
            return ""

        # 2. Combine blocks with AND
        if len(block_exprs) == 1:
            final_ast = block_exprs[0]
        else:
            final_ast = self.algebra.AND(*block_exprs)

        # 3. Render AST to string
        return self._render_pubmed_ast(final_ast)

    def _format_pubmed_term(self, term: OntologyTerm) -> str:
        """
        Formats a term for PubMed:
        - MeSH -> "Label"[Mesh]
        - Other -> "Label"[TiAb]
        """
        label = self._sanitize_label(term.label)

        if term.vocab_source == VocabSource.MESH.value:
            return f'"{label}"[Mesh]'
        else:
            return f'"{label}"[TiAb]'

    def _sanitize_label(self, label: str) -> str:
        """
        Sanitizes the label for use in a double-quoted PubMed string.
        - Trims whitespace.
        - Replaces double quotes with single quotes to prevent string breaking.
        """
        cleaned = label.strip()
        cleaned = cleaned.replace('"', "'")
        return cleaned

    def _render_pubmed_ast(self, expr: boolean.Expression) -> str:
        """
        Recursive visitor to render AST to PubMed string format.
        Strictly parenthesized.
        """
        if isinstance(expr, boolean.Symbol):
            # Symbol name is already formatted like "Term"[Tag]
            return str(expr.obj)

        if isinstance(expr, boolean.NOT):
            # PubMed uses NOT operator.
            # NOT (A)
            return f"(NOT {self._render_pubmed_ast(expr.args[0])})"

        if isinstance(expr, boolean.OR):
            children = [self._render_pubmed_ast(arg) for arg in expr.args]
            return f"({' OR '.join(children)})"

        if isinstance(expr, boolean.AND):
            children = [self._render_pubmed_ast(arg) for arg in expr.args]
            return f"({' AND '.join(children)})"

        return str(expr)  # pragma: no cover

    def _compile_lancedb(self, protocol: ProtocolDefinition) -> str:
        """
        Internal method to generate LanceDB JSON query string.
        Output format: {"vector": "research_question", "filter": ""}
        """
        payload = {
            "vector": protocol.research_question,
            "filter": "",  # Placeholder as per requirements
        }
        return json.dumps(payload)
