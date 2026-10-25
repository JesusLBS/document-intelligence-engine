import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import Config


def configure_logging() -> None:
    """
    Configure root logging with console and file handlers.

    Sets up formatting, log level from env, and writes to storage/logs/app.log
    (rotated at 5 MB, 3 backups) while keeping stdout output for Docker/console visibility.
    """
    log_dir = "storage/logs"
    os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(os.path.join(log_dir, "app.log"), maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)