"""Logging setup for SLI Recorder."""

from __future__ import annotations

import logging
import sys


def setup_logging(*, verbose: bool = False) -> logging.Logger:
    """Set up logging for the application.
    
    Args:
        verbose: Enable debug-level logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("sli_recorder")

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Set level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        formatter = logging.Formatter("%(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_command(logger: logging.Logger, cmd: list[str]) -> None:
    """Log a command that will be executed.
    
    Args:
        logger: Logger instance
        cmd: Command and arguments list
    """
    logger.debug("Executing: %s", " ".join(cmd))


def log_process_result(
    logger: logging.Logger,
    process_name: str,
    return_code: int,
    stderr: str | None = None,
) -> None:
    """Log the result of a process execution.
    
    Args:
        logger: Logger instance
        process_name: Name of the process for logging
        return_code: Process return code
        stderr: Optional stderr output
    """
    if return_code == 0:
        logger.debug("%s completed successfully", process_name)
    else:
        logger.error("%s failed with return code %d", process_name, return_code)
        if stderr:
            logger.error("%s stderr: %s", process_name, stderr.strip())


def log_recording_status(
    logger: logging.Logger,
    output_path: str,
    elapsed_seconds: int,
) -> None:
    """Log recording status with elapsed time.
    
    Args:
        logger: Logger instance
        output_path: Path to output file
        elapsed_seconds: Elapsed recording time
    """
    hours, remainder = divmod(elapsed_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    logger.info("%s recording… press Ctrl+C to stop", time_str)


def format_elapsed_time(seconds: int) -> str:
    """Format elapsed time in HH:MM:SS format.
    
    Args:
        seconds: Total elapsed seconds
        
    Returns:
        Formatted time string
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
