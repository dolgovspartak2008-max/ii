"""Logging configuration for process entry points."""

import logging


def configure_logging(level: str) -> None:
    """Configure the standard application log format."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
