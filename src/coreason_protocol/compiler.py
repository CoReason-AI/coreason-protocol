"""Compiler module for converting ProtocolDefinitions into executable strategies."""

import json
from typing import Dict, Iterator, List, Protocol, Tuple

import boolean
from coreason_identity.models import UserContext

from coreason_protocol.types import (
    ExecutableStrategy,
    OntologyTerm,
    PicoBlock,
    ProtocolDefinition,
    Target,
    VocabSource,
)
from coreason_protocol.utils.logger import logger


class CompilerStrategy(Protocol):
    """Interface for target-specific strategy compilers."""

    def compile(self, protocol: ProtocolDefinition) -> str:
        """Compiles the protocol into a target-specific query string.

        Args:
            protocol: The protocol to compile.

        Returns:
            str: The compiled query string.
        """
        ...


class BaseCompiler:
    """Base class containing common logic for PICO block iteration."""

    def _iter_active_blocks(self, protocol: ProtocolDefinition) -> Iterator[Tuple[PicoBlock, List[OntologyTerm]]]:
        """Iterates over PICO blocks in standard order (P, I, C, O, S).

        Yields only blocks that are present and have at least one active term.

        Args:
            protocol: The protocol to iterate.

        Yields:
            Tuple[PicoBlock, List[OntologyTerm]]: A tuple containing the block and its list of active terms.
        """
        order = ["P", "I", "C", "O", "S"]
        for block_type in order:
            if block_type in protocol.pico_structure:
                block = protocol.pico_structure[block_type]
                active_terms = [t for t in block.terms if t.is_active]
                if active_terms:
                    yield block, active_terms


class PubMedCompiler(BaseCompiler):
    """Strategy for compiling protocols to PubMed query strings."""

    def __init__(self) -> None:
        """Initialize the Boolean algebra engine."""
        self.algebra = boolean.BooleanAlgebra()

    def compile(self, protocol: ProtocolDefinition) -> str:
        """Generates PubMed/Ovid boolean strings.

        Logic: (P) AND (I) AND (C) AND (O) AND (S)

        Args:
            protocol: The protocol to compile.

        Returns:
            str: The compiled PubMed query string.
        """
        block_exprs = []

        for block, active_terms in self._iter_active_blocks(protocol):
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
        """Formats a term for PubMed.

        - MeSH -> "Label"[Mesh]
        - Other -> "Label"[TiAb]

        Args:
            term: The ontology term to format.

        Returns:
            str: The formatted term string.
        """
        label = self._sanitize_label(term.label)

        if term.vocab_source == VocabSource.MESH.value:
            return f'"{label}"[Mesh]'
        else:
            return f'"{label}"[TiAb]'

    def _sanitize_label(self, label: str) -> str:
        """Sanitizes the label for use in a double-quoted PubMed string.

        - Trims whitespace.
        - Replaces double quotes with single quotes to prevent string breaking.

        Args:
            label: The label to sanitize.

        Returns:
            str: The sanitized label.
        """
        cleaned = label.strip()
        cleaned = cleaned.replace('"', "'")
        return cleaned

    def _render_pubmed_ast(self, expr: boolean.Expression) -> str:
        """Recursive visitor to render AST to PubMed string format.

        Strictly parenthesized.

        Args:
            expr: The boolean expression to render.

        Returns:
            str: The rendered string.
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


class LanceDBCompiler(BaseCompiler):
    """Strategy for compiling protocols to LanceDB queries."""

    def compile(self, protocol: ProtocolDefinition) -> str:
        """Internal method to generate LanceDB JSON query string.

        Output format: {"vector": "research_question", "filter": ""}

        Args:
            protocol: The protocol to compile.

        Returns:
            str: JSON string representing the LanceDB query.
        """
        payload = {
            "vector": protocol.research_question,
            "filter": "",  # Placeholder as per requirements
        }
        return json.dumps(payload)


class GraphCompiler(BaseCompiler):
    """Strategy for compiling protocols to Graph (Cypher) queries."""

    def compile(self, protocol: ProtocolDefinition) -> str:
        """Generates Cypher traversal logic.

        Matches publications containing terms from all required PICO blocks.
        Logic:
          - Inter-block: AND (Chain of MATCH ... WITH p ...)
          - Intra-block: OR (WHERE t.code IN [...])

        Args:
            protocol: The protocol to compile.

        Returns:
            str: The generated Cypher query.
        """
        block_constraints = []
        for _, active_terms in self._iter_active_blocks(protocol):
            # Create a list of sanitized, quoted codes for each block
            codes_list = [self._escape_cypher_string(t.code) for t in active_terms]
            if codes_list:
                block_constraints.append(codes_list)

        if not block_constraints:
            return ""

        parts = []
        for i, codes in enumerate(block_constraints):
            # Join codes into a Cypher list: ['C1', 'C2']
            codes_str = f"[{', '.join(codes)}]"

            if i == 0:
                parts.append(f"MATCH (p:Publication)-[:HAS_MESH]->(t:Term) WHERE t.code IN {codes_str}")
            else:
                parts.append(f"WITH p MATCH (p)-[:HAS_MESH]->(t:Term) WHERE t.code IN {codes_str}")

        parts.append("RETURN p")
        return " ".join(parts)

    def _escape_cypher_string(self, value: str) -> str:
        """Escapes a string for use in a Cypher single-quoted string literal.

        Handles backslashes and single quotes.

        Args:
            value: The string to escape.

        Returns:
            str: The escaped string.
        """
        # Order matters: replace backslash first, then single quote
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"


class StrategyCompiler:
    """Compiles ProtocolDefinition into executable search strategies for various targets.

    Uses the Strategy Pattern to delegate compilation to target-specific implementations.
    """

    def __init__(self) -> None:
        """Initialize the compiler with supported strategies."""
        self._compilers: Dict[str, CompilerStrategy] = {
            Target.PUBMED.value: PubMedCompiler(),
            Target.LANCEDB.value: LanceDBCompiler(),
            Target.GRAPH.value: GraphCompiler(),
        }

    def compile(
        self, protocol: ProtocolDefinition, context: UserContext, target: str = Target.PUBMED.value
    ) -> ExecutableStrategy:
        """Compiles the protocol for a specific target.

        Args:
            protocol: The protocol to compile.
            context: User identity context.
            target: The target execution engine (default: "PUBMED").

        Returns:
            ExecutableStrategy: Object containing the compiled query string.

        Raises:
            ValueError: If the target is not supported.
        """
        logger.debug("Compiler started", user_id=context.user_id)
        logger.debug(f"Compiling protocol {protocol.id} for target {target}")

        compiler = self._compilers.get(target)
        if not compiler:
            logger.error(f"Unsupported target requested: {target}")
            raise ValueError(f"Unsupported target: {target}")

        query_string = compiler.compile(protocol)

        logger.info(f"Successfully compiled protocol {protocol.id} for {target}")

        return ExecutableStrategy(
            target=target,
            query_string=query_string,
            validation_status="PRESS_PASSED",  # Placeholder until validation logic exists
        )
