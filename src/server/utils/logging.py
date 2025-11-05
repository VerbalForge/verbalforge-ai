"""
Logging Configuration

Centralized logging setup for the server with separate log files per runner.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(
    log_level: str = "INFO", log_file: str = "logs/verbalforge.log"
) -> logging.Logger:
    """
    Setup main server logging and create separate log files for each runner
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Main server log file path (will be timestamped)
        
    Returns:
        Main server logger
    """
    # Ensure log directory exists
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)
    
    # Create timestamped log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create timestamped filenames
    main_log = log_dir / f"verbalforge_{timestamp}.log"
    tc_log = log_dir / f"tc_runner_{timestamp}.log"
    se_log = log_dir / f"se_runner_{timestamp}.log"
    rc_log = log_dir / f"rc_runner_{timestamp}.log"

    # Setup root logging configuration
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(main_log, mode="w"),  # Write mode for new file
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    # Create main server logger
    logger = logging.getLogger("VerbalForgeServer")
    logger.info("=" * 60)
    logger.info("VerbalForge Question Generation Server")
    logger.info("=" * 60)
    logger.info(f"Session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Main log file: {main_log}")
    
    # Setup separate log files for each runner
    _setup_runner_logging("VerbalForgeServer.Runners.TC", tc_log, log_level)
    _setup_runner_logging("VerbalForgeServer.Runners.SE", se_log, log_level)
    _setup_runner_logging("VerbalForgeServer.Runners.RC", rc_log, log_level)
    
    logger.info(f"Runner logs:")
    logger.info(f"  - TC Runner: {tc_log}")
    logger.info(f"  - SE Runner: {se_log}")
    logger.info(f"  - RC Runner: {rc_log}")

    return logger


def _setup_runner_logging(logger_name: str, log_file: Path, log_level: str) -> None:
    """
    Setup logging for a specific runner with its own file
    
    Args:
        logger_name: Name of the logger (e.g., "VerbalForgeServer.Runners.TC")
        log_file: Path to the runner's log file
        log_level: Logging level
    """
    runner_logger = logging.getLogger(logger_name)
    
    # Create file handler for this runner
    file_handler = logging.FileHandler(log_file, mode="w")  # Write mode for new file
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # Add the file handler to the runner's logger
    runner_logger.addHandler(file_handler)
    
    # Also keep console output (inherited from root)
    runner_logger.propagate = True
