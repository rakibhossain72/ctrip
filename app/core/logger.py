"""
Centralized logger configuration with rotating file logs.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

# Define log directory and file
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Create logs directory if it doesn't exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def setup_logging(level=logging.INFO):
    """
    Sets up the logging configuration with both console and rotating file handlers.
    """
    # Create a custom logging format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    # Rotating File Handler (10 MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(log_format)

    # Root Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Specific logger for this app
    app_logger = logging.getLogger("app")
    app_logger.info("Logging initialized. Logs are saved in %s", LOG_FILE)

    # Silence arq worker logs
    logging.getLogger("arq").setLevel(logging.WARNING)
    logging.getLogger("arq.worker").setLevel(logging.WARNING)


# Initialize logging immediately upon module import
setup_logging()

# Provide a logger instance for the core module
logger = logging.getLogger("app")
