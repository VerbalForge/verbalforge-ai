"""Logging configuration for VerbalForge MCP"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

from .settings import settings


def generate_session_log_filename(base_log_file: str) -> str:
    """
    Generate a unique log filename for each session based on timestamp

    Args:
        base_log_file: Base log file path from settings

    Returns:
        Unique log file path with timestamp
    """
    # Get the directory and base name
    log_dir = os.path.dirname(base_log_file)
    base_name = os.path.basename(base_log_file)

    # Split filename and extension
    name, ext = os.path.splitext(base_name)

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create new filename with timestamp
    session_filename = f"{name}_{timestamp}{ext}"
    session_log_path = os.path.join(log_dir, session_filename)

    return session_log_path


def setup_logging(
    level: Optional[str] = None, log_file: Optional[str] = None, console_output: bool = True
) -> logging.Logger:
    # Use settings defaults if not provided
    log_level = level or settings.log_level

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("core")
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Only add file handler if explicitly requested (for standalone/CLI use)
    if log_file:
        log_file_path = generate_session_log_filename(log_file)

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"File logging enabled - File: {log_file_path}")

    # Console handler (for standalone use)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Allow propagation to root logger (so server can capture logs)
    logger.propagate = True

    logger.info(f"Core logging initialized - Level: {log_level}")

    return logger


def get_logger(name: str = "verbalforge") -> logging.Logger:
    """
    Get a logger instance for a specific module

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    # Ensure main logger is set up
    main_logger = logging.getLogger("verbalforge")
    if not main_logger.handlers:
        setup_logging()

    # Return child logger
    return logging.getLogger(f"verbalforge.{name}")


def enable_debug_logging():
    """Enable debug level logging"""
    logger = logging.getLogger("verbalforge")
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers:
        handler.setLevel(logging.DEBUG)
    logger.info("Debug logging enabled")


def get_log_file_path() -> str:
    """Get the current session log file path"""
    # Get the logger and check if it has file handlers
    logger = logging.getLogger("verbalforge")
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return os.path.abspath(handler.baseFilename)

    # Fallback to generating a new session filename
    return os.path.abspath(generate_session_log_filename(settings.log_file))


def get_latest_log_file() -> str:
    """Get the path to the most recent log file in the logs directory"""
    log_dir = os.path.dirname(settings.log_file)
    base_name = os.path.splitext(os.path.basename(settings.log_file))[0]

    if not os.path.exists(log_dir):
        return get_log_file_path()

    # Find all log files matching the pattern
    log_files = []
    for filename in os.listdir(log_dir):
        if filename.startswith(base_name) and filename.endswith(".log"):
            full_path = os.path.join(log_dir, filename)
            log_files.append((full_path, os.path.getmtime(full_path)))

    if not log_files:
        return get_log_file_path()

    # Return the most recent file
    latest_file = max(log_files, key=lambda x: x[1])[0]
    return os.path.abspath(latest_file)


def view_recent_logs(lines: int = 50, log_file_path: Optional[str] = None) -> str:
    """
    Get recent log entries

    Args:
        lines: Number of recent lines to return
        log_file_path: Specific log file to read (uses current session if None)

    Returns:
        Recent log entries as string
    """
    if log_file_path is None:
        log_file_path = get_log_file_path()

    if not os.path.exists(log_file_path):
        return f"No log file found at {log_file_path}. Logging may not be initialized."

    try:
        with open(log_file_path, "r") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return "".join(recent_lines)
    except Exception as e:
        return f"Error reading log file: {e}"


def list_log_files() -> list:
    """
    List all log files in the logs directory

    Returns:
        List of tuples (filename, full_path, modification_time)
    """
    log_dir = os.path.dirname(settings.log_file)
    base_name = os.path.splitext(os.path.basename(settings.log_file))[0]

    if not os.path.exists(log_dir):
        return []

    log_files = []
    for filename in os.listdir(log_dir):
        if filename.startswith(base_name) and filename.endswith(".log"):
            full_path = os.path.join(log_dir, filename)
            mod_time = os.path.getmtime(full_path)
            log_files.append((filename, full_path, mod_time))

    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x[2], reverse=True)
    return log_files
