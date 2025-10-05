"""
Logging Configuration

Centralized logging setup for the server.
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    log_level: str = "INFO", log_file: str = "logs/verbalforge.log"
) -> logging.Logger:

    # Ensure log directory exists
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),  # Append mode
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    logger = logging.getLogger("VerbalForgeServer")
    logger.info("=" * 60)
    logger.info("VerbalForge Question Generation Server")
    logger.info("=" * 60)
    logger.info(f"Log file: {log_file}")

    return logger
