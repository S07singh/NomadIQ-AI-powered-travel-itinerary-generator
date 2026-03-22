"""
Logging configuration for NomadIQ using Loguru.
"""

import sys
from loguru import logger


def setup_logging(console_level: str = "INFO") -> None:
    """Configure loguru logging with console output."""
    # Remove default handler
    logger.remove()

    # Add console handler with formatting
    logger.add(
        sys.stdout,
        level=console_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Add file handler for debug logs
    logger.add(
        "logs/nomadiq.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    )
