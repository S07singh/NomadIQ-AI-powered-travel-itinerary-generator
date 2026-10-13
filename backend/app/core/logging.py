"""Loguru logging setup."""

import sys

from loguru import logger


def setup_logging(level: str = "INFO", log_to_file: bool = True) -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
        ),
    )
    if log_to_file:
        logger.add(
            "logs/nomadiq.log",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        )
