import logging
import sys
from typing import Union


class MaxLevelFilter(logging.Filter):
    """Allow only records up to a maximum level (inclusive)."""

    def __init__(self, max_level: int):
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        return record.levelno <= self.max_level


def _normalize_level(level: Union[str, int]) -> int:
    """Normalize a string/int log level to an int, or raise ValueError."""
    if isinstance(level, int):
        if level in (
            logging.CRITICAL,
            logging.ERROR,
            logging.WARNING,
            logging.INFO,
            logging.DEBUG,
            logging.NOTSET,
        ):
            return level
        raise ValueError(f"Invalid numeric log level: {level}")
    if isinstance(level, str):
        name = level.strip().upper()
        if hasattr(logging, name):
            value = getattr(logging, name)
            if isinstance(value, int):
                return value
    raise ValueError(f"Invalid log level: {level!r}")


def get_logger(name: str, level: Union[str, int] = "INFO") -> logging.Logger:
    """
    Create (or fetch) a logger that routes:
      * DEBUG–WARNING  → stdout
      * ERROR and above → stderr

    Note:
      - logger.setLevel(level) is the global minimum; DEBUG messages are dropped if level > DEBUG.
      - Handlers are attached only once per logger.
    """
    logger = logging.getLogger(name)
    lvl = _normalize_level(level)

    # If already configured, just adjust its level and return.
    if logger.handlers:
        logger.setLevel(lvl)
        return logger

    # ---------- Formatter ----------
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # ---------- Handler: stdout (<= WARNING) ----------
    h_out = logging.StreamHandler(sys.stdout)
    h_out.setLevel(logging.DEBUG)  # let the filter cap the upper bound
    h_out.addFilter(MaxLevelFilter(logging.WARNING))
    h_out.setFormatter(fmt)
    # Optional: tag to avoid accidental duplicate adds by external code
    h_out.name = f"{name}-stdout"

    # ---------- Handler: stderr (>= ERROR) ----------
    h_err = logging.StreamHandler(sys.stderr)
    h_err.setLevel(logging.ERROR)
    h_err.setFormatter(fmt)
    h_err.name = f"{name}-stderr"

    # ---------- Register handlers ----------
    logger.addHandler(h_out)
    logger.addHandler(h_err)
    logger.setLevel(lvl)

    # Prevent double-logging through the root logger.
    logger.propagate = False

    return logger
