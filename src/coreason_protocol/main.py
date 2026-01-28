# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

import argparse
import json
import sys
from typing import Optional

from coreason_identity.models import UserContext

from coreason_protocol import ProtocolDefinition, ProtocolService, __author__, __version__
from coreason_protocol.utils.logger import logger
from coreason_protocol.validator import ProtocolValidator


def get_system_context() -> UserContext:
    """Creates a local system identity context for CLI operations."""
    return UserContext(
        user_id="cli-user",
        email="cli@coreason.ai",
        groups=["system"],
        scopes=["*"],
        claims={"source": "cli"},
    )


def load_protocol(path: str) -> Optional[ProtocolDefinition]:
    """Loads a ProtocolDefinition from a JSON file."""
    try:
        with open(path, "r") as f:
            data = json.load(f)
        proto = ProtocolDefinition.model_validate(data)
        # Ensure correct type is returned for mypy
        if isinstance(proto, ProtocolDefinition):
            return proto
        return None  # Should not happen if validation succeeds
    except Exception as e:
        logger.error(f"Failed to load protocol from {path}: {e}")
        return None


def compile_command(args: argparse.Namespace) -> None:
    """Handles the compile command."""
    context = get_system_context()
    protocol = load_protocol(args.protocol)
    if not protocol:
        sys.exit(1)

    with ProtocolService() as service:
        try:
            strategies = service.compile_protocol(protocol, args.target, context)
            for s in strategies:
                print(f"Target: {s.target}")
                print(f"Query: {s.query_string}")
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            sys.exit(1)


def validate_command(args: argparse.Namespace) -> None:
    """Handles the validate command."""
    # Note: Validation primarily checks structure and rules.
    # While not strictly needing context for logic, we log the action with context.
    context = get_system_context()
    logger.info("Starting validation", user_id=context.user_id)

    protocol = load_protocol(args.protocol)
    if not protocol:
        sys.exit(1)

    try:
        ProtocolValidator.validate(protocol)
        print("Protocol is valid.")
        logger.info("Protocol validation successful")
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


def run_command(args: argparse.Namespace) -> None:
    """Handles the run command."""
    context = get_system_context()
    logger.info("Run command invoked", user_id=context.user_id)

    # Placeholder for execution logic
    print("Execution logic not implemented yet.")


def main() -> None:
    """Entry point for the package CLI."""
    parser = argparse.ArgumentParser(description=f"coreason-protocol v{__version__}")
    subparsers = parser.add_subparsers(dest="command")

    # Compile
    compile_parser = subparsers.add_parser("compile", help="Compile a protocol")
    compile_parser.add_argument("protocol", help="Path to protocol JSON file")
    compile_parser.add_argument("--target", default="PUBMED", help="Target execution engine")

    # Validate
    validate_parser = subparsers.add_parser("validate", help="Validate a protocol")
    validate_parser.add_argument("protocol", help="Path to protocol JSON file")

    # Run
    run_parser = subparsers.add_parser("run", help="Run a protocol")
    run_parser.add_argument("protocol", help="Path to protocol JSON file")

    args = parser.parse_args()

    if args.command == "compile":
        compile_command(args)
    elif args.command == "validate":
        validate_command(args)
    elif args.command == "run":
        run_command(args)
    else:
        info = f"coreason-protocol v{__version__} by {__author__}"
        logger.info(info)
        print(info)
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
