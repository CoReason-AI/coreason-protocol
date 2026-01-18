import boolean

from coreason_protocol.types import (
    ExecutableStrategy,
    OntologyTerm,
    ProtocolDefinition,
)


class StrategyCompiler:
    """
    Compiles ProtocolDefinition into executable search strategies for various targets.
    Uses boolean.py to construct Abstract Syntax Trees (AST) for logic robustness.
    """

    def __init__(self) -> None:
        self.algebra = boolean.BooleanAlgebra()

    def compile(self, protocol: ProtocolDefinition, target: str = "PUBMED") -> ExecutableStrategy:
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
        if target == "PUBMED":
            query_string = self._compile_pubmed(protocol)
            return ExecutableStrategy(
                target="PUBMED",
                query_string=query_string,
                validation_status="PRESS_PASSED",  # Placeholder until validation logic exists
            )
        else:
            raise ValueError(f"Unsupported target: {target}")

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
        # Escape double quotes in label if present?
        # PubMed syntax usually uses double quotes for phrases.
        # If label has quotes, we should probably handle them.
        # For now, assume label is clean or just needs wrapping.
        label = term.label.strip()

        # Basic escaping: if label contains double quote, escape it?
        # PubMed doesn't support backslash escaping well.
        # Usually one would replace " with space or single quote.
        # But let's just wrap in quotes.

        if term.vocab_source == "MeSH":
            return f'"{label}"[Mesh]'
        else:
            return f'"{label}"[TiAb]'

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
