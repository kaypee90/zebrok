import logging
import os

from .config import LOG_FILE, LOG_LEVEL

ROOT_LOGGER_NAME = "zebrok"

_FORMAT = "{asctime} - {name} - {levelname} - {message}"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _FallbackConsoleHandler(logging.StreamHandler):
    """
    Prints zebrok's logs to the console only while the application has not
    configured logging itself. Once the root logger has handlers (e.g. after
    logging.basicConfig()), records reach them by normal propagation instead,
    so nothing is printed twice.
    """

    def emit(self, record: logging.LogRecord) -> None:
        if not logging.getLogger().handlers:
            super().emit(record)


def _configure_root_logger() -> None:
    """
    Configures the "zebrok" parent logger once. Module loggers are children
    of it, so `logging.getLogger("zebrok").setLevel(...)` controls them all.
    """
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    if any(getattr(h, "_zebrok", False) for h in logger.handlers):
        return

    level = os.environ.get("ZEBROK_LOG_LEVEL", LOG_LEVEL).upper()
    is_known_level = isinstance(logging.getLevelName(level), int)
    logger.setLevel(level if is_known_level else LOG_LEVEL)

    formatter = logging.Formatter(_FORMAT, style="{", datefmt=_DATE_FORMAT)
    handlers: list[logging.Handler] = [_FallbackConsoleHandler()]
    log_file = os.environ.get("ZEBROK_LOG_FILE", LOG_FILE)
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    for handler in handlers:
        handler._zebrok = True  # type: ignore[attr-defined]
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def create_logger(module_name: str) -> logging.Logger:
    """
    Returns the logger for a module.

    Handlers live only on the "zebrok" parent logger and are attached once,
    so loggers are never duplicated. Output goes to the console unless the
    application configured logging itself; set ZEBROK_LOG_FILE to also write
    to a file, and ZEBROK_LOG_LEVEL to change the level (default INFO).

    parameters:
        module_name (str): name of module importing the logger
    """
    _configure_root_logger()
    return logging.getLogger(module_name)
