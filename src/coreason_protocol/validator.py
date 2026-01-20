"""Validator logic for ProtocolDefinition."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from coreason_protocol.types import ProtocolDefinition


class ProtocolValidator:
    """Validator for ProtocolDefinition structural integrity.

    Ensures P/I/O blocks are present and not empty, and checks term validity.
    """

    REQUIRED_BLOCKS = frozenset({"P", "I", "O"})
    VALID_LOGIC_OPERATORS = frozenset({"AND", "OR", "NOT"})

    @classmethod
    def validate(cls, protocol: "ProtocolDefinition") -> None:
        """Validates the protocol structure against PRESS guidelines and internal consistency rules.

        Checks:
        1. Structural Integrity: P, I, O blocks must exist and contain at least one term.
        2. Logic Validity: Boolean operators (AND, OR, NOT) must be valid.
        3. Term Validity: Active terms must have non-empty labels and codes.

        Args:
            protocol: The protocol definition to validate.

        Raises:
            ValueError: If the protocol fails any validation check.
        """
        pico = protocol.pico_structure

        # 1. Structural Integrity: Ensure P, I, O blocks are not empty
        for block_type in cls.REQUIRED_BLOCKS:
            if block_type not in pico:
                raise ValueError(f"Missing required block: '{block_type}'")

            block = pico[block_type]
            if not block.terms:
                raise ValueError(f"Block '{block_type}' cannot be empty")

        # 2. Logic Validity: Verify Boolean operators
        # Iterate over all blocks, not just required ones (include C and S if present)
        for block_key, block in pico.items():
            if block.logic_operator not in cls.VALID_LOGIC_OPERATORS:
                raise ValueError(f"Block '{block_key}' has invalid logic_operator: '{block.logic_operator}'")

            # 3. Term Validity: Check for 'empty' terms (active terms with no label/code)
            for term in block.terms:
                if term.is_active:
                    if not term.label or not term.label.strip():
                        raise ValueError(f"Active term in block '{block_key}' has empty label (ID: {term.id})")
                    if not term.code or not term.code.strip():
                        raise ValueError(f"Active term in block '{block_key}' has empty code (ID: {term.id})")
