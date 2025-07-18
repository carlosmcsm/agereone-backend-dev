import logging
import os
from logging.handlers import TimedRotatingFileHandler

# -------------- CONFIGURATION -------------------

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "agereone_backend.log")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# -------------- CONSOLE FORMATTER ----------------

class ConsoleFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m\033[97m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

# -------------- LOGGER INITIALIZATION ------------

def init_logging():
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    # File handler: daily rotation, keep 7 days
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    file_handler.setLevel(LOG_LEVEL)

    # Console handler: colored output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ConsoleFormatter(LOG_FORMAT, DATE_FORMAT))
    console_handler.setLevel(LOG_LEVEL)

    # Avoid duplicate logs
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    else:
        # Clear and reset handlers if already present
        logger.handlers = []
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Make FastAPI/Uvicorn logs go through our logger
    for uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uvicorn_logger)
        uv_logger.handlers = []
        uv_logger.propagate = True

# -------------- USAGE EXAMPLE -------------------

# In every file: (at the top)
# from app.core.logging import init_logging
# init_logging()
# import logging
# logger = logging.getLogger(__name__)

# Then use logger.info, logger.error, etc. everywhere!

if __name__ == "__main__":
    init_logging()
    logger = logging.getLogger(__name__)
    logger.info("AgereOne logging initialized!")
    try:
        raise ValueError("Example error for logging")
    except Exception as e:
        logger.error("An exception occurred!", exc_info=True)
