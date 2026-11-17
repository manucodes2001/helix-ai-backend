"""Structured logging configuration with automatic API secret redaction."""

from __future__ import annotations

import logging
import re
from pathlib import Path


class SecretRedactingFilter(logging.Filter):
    """Mask OpenAI keys and NCBI api_key query parameters in log output."""

    _PATTERNS = [
        re.compile(r"(sk-[A-Za-z0-9_-]{10,})"),
        re.compile(r"(api_key=)([A-Za-z0-9_-]+)", re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage())
        for pat in self._PATTERNS:
            if pat.groups == 2:
                message = pat.sub(r"\1***REDACTED***", message)
            else:
                message = pat.sub("***REDACTED***", message)
        record.msg = message
        record.args = ()
        return True


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("helix_ai")
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redactor = SecretRedactingFilter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redactor)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redactor)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"helix_ai.{name}")
