import sys
from loguru import logger
from .config import Config


def setup_logger():
    """Configure and setup application-wide logging"""

    # Remove default logger
    logger.remove()

    # Console logging with colored output
    logger.add(
        sys.stderr,
        level=Config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )

    # File logging with rotation
    logger.add(
        Config.LOG_FILE,
        level=Config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=Config.LOG_ROTATION,
        retention=Config.LOG_RETENTION,
        compression="zip",
        encoding="utf-8"
    )

    return logger


# Create global logger instance
app_logger = setup_logger()


def get_logger(name: str = None):
    """Get a logger instance with optional name binding"""
    if name:
        return app_logger.bind(name=name)
    return app_logger