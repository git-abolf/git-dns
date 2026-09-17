"""Central logging setup shared by the desktop, mobile and CLI front-ends.

Writes a rotating log file under the same per-OS app-data directory used by
storage.py, and mirrors warnings/errors to stderr. Import `get_logger()` and
use it instead of bare `except: pass` so problems are recorded somewhere the
user (or a support request) can actually find them.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from app.core.storage import data_dir

_LOGGER_NAME = "dnsmasterpro"
_configured = False


def _log_path():
    return os.path.join(data_dir(), "dnsmasterpro.log")


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return the app logger, configuring handlers exactly once."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if not _configured:
        logger.setLevel(logging.INFO)
        try:
            file_handler = RotatingFileHandler(
                _log_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
            )
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            logger.addHandler(file_handler)
        except OSError:
            # If we can't write a log file (e.g. read-only install dir), fall
            # back to console-only logging rather than crashing the app.
            pass

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(console_handler)
        _configured = True

    if name == _LOGGER_NAME:
        return logger
    return logger.getChild(name)
