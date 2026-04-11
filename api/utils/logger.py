import os
import sys
from loguru import logger

SERVER_VERSION = "0.1.1"
_logger_initialized = False
DEFAULT_SELECTED_MODULE = "00000000000000"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "server.log"








def formatter(record):
    """Add default values for missing fields used by the logger format."""
    record["extra"].setdefault("tag", record["name"])
    # Use the default module string when it is not provided.
    record["extra"].setdefault("selected_module", DEFAULT_SELECTED_MODULE)
    # Mirror selected_module at top level for format compatibility.
    record["selected_module"] = record["extra"]["selected_module"]
    return record["message"]


def setup_logging():
    """Configure console and file logging with in-project defaults."""
    global _logger_initialized

    # Configure the logger only once.
    if not _logger_initialized:
        api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(api_dir, "logs")
        log_file_path = os.path.join(log_dir, DEFAULT_LOG_FILE)

        os.makedirs(log_dir, exist_ok=True)

        # Initialize extras with default selected module.
        logger.configure(
            extra={
                "selected_module": DEFAULT_SELECTED_MODULE,
            }
        )

        log_format = (
            "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}]"
            "[<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-"
            "<light-green>{message}</light-green>"
        )
        log_format_file = (
            "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - "
            "{name} - {level} - {extra[tag]} - {message}"
        )
        log_format = log_format.replace("{version}", SERVER_VERSION)
        log_format_file = log_format_file.replace("{version}", SERVER_VERSION)

        log_level = DEFAULT_LOG_LEVEL

        # Reset existing handlers and configure outputs.
        logger.remove()

        # Console output.
        logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter)

        # File output in api/logs with size-based rotation.
        logger.add(
            log_file_path,
            format=log_format_file,
            level=log_level,
            filter=formatter,
            rotation="10 MB",  # Max 10 MB per file.
            retention="30 days",  # Keep logs for 30 days.
            compression=None,
            encoding="utf-8",
            enqueue=True,  # Async-safe logging.
            backtrace=True,
            diagnose=True,
        )
        _logger_initialized = True  # Mark logger as initialized.

    return logger

