"""Simple logger with contextvars-based trace IDs for the environment."""

from __future__ import annotations

import logging
import sys
import threading
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


class _TraceFilter(logging.Filter):
    """Injects the current trace_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get("")
        return True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a configured logger that always emits trace IDs."""
    logger = logging.getLogger(name or "openenv_multidomain")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = "%(asctime)s %(name)s %(levelname)s [trace=%(trace_id)s] %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    handler.addFilter(_TraceFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
