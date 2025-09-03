"""Path handling utilities for SLI Recorder."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def sanitize_title(title: str) -> str:
    """Sanitize a title for use in filenames.
    
    Args:
        title: The raw title string
        
    Returns:
        Sanitized title safe for filenames
    """
    # Replace spaces with hyphens and remove unsafe characters
    sanitized = re.sub(r"[^\w\s-]", "", title)
    sanitized = re.sub(r"[-\s]+", "-", sanitized)
    return sanitized.strip("-").lower()


def build_output_filename(title: str | None = None) -> str:
    """Build the output filename with timestamp and optional title.
    
    Args:
        title: Optional title to include in filename
        
    Returns:
        Filename in format: YYYYmmdd-HHMMSS[--sanitized-title].mp3
    """
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")

    if title:
        sanitized = sanitize_title(title)
        if sanitized:
            return f"{timestamp}--{sanitized}.mp3"

    return f"{timestamp}.mp3"


def ensure_output_dir(outdir: Path) -> None:
    """Ensure the output directory exists.
    
    Args:
        outdir: Path to the output directory
        
    Raises:
        OSError: If directory cannot be created
    """
    outdir.mkdir(parents=True, exist_ok=True)


def check_output_file(output_path: "Path", *, overwrite: bool) -> None:
    """Check if output file exists and handle overwrite logic.
    
    Args:
        output_path: Path to the output file
        overwrite: Whether to allow overwriting existing files
        
    Raises:
        FileExistsError: If file exists and overwrite is False
    """
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. "
            "Use --overwrite to replace it.",
        )
