# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_protocol

from coreason_protocol import __author__, __version__
from coreason_protocol.utils.logger import logger


def main() -> None:
    """Entry point for the package."""
    info = f"coreason-protocol v{__version__} by {__author__}"
    logger.info(info)
    print(info)


if __name__ == "__main__":  # pragma: no cover
    main()
