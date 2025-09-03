"""Binary detection and system checks for SLI Recorder."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class BinaryNotFoundError(Exception):
    """Raised when a required binary cannot be found."""


class DetectPermissionError(Exception):
    """Raised when system permissions are not granted."""


def find_system_audio_dump(custom_path: Path | None = None) -> Path:
    """Find the SystemAudioDump binary.
    
    Args:
        custom_path: Optional custom path to the binary
        
    Returns:
        Path to the SystemAudioDump binary
        
    Raises:
        BinaryNotFoundError: If binary cannot be found or is not executable
    """
    if custom_path:
        if not custom_path.exists():
            raise BinaryNotFoundError(f"SystemAudioDump not found at: {custom_path}")
        if not custom_path.is_file() or not _is_executable(custom_path):
            raise BinaryNotFoundError(f"SystemAudioDump is not executable: {custom_path}")
        return custom_path

    # Common locations to check
    candidates = [
        Path("./SystemAudioDump"),
        Path("./.build/release/SystemAudioDump"),
        Path("./externals/systemAudioDump/.build/release/SystemAudioDump"),
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and _is_executable(candidate):
            return candidate

    raise BinaryNotFoundError(
        "SystemAudioDump binary not found. Please specify path with --dump-bin or "
        "build it using: swift build -c release",
    )


def find_ffmpeg(custom_path: str | None = None) -> Path:
    """Find the ffmpeg binary.
    
    Args:
        custom_path: Optional custom path to ffmpeg
        
    Returns:
        Path to the ffmpeg binary
        
    Raises:
        BinaryNotFoundError: If ffmpeg cannot be found
    """
    if custom_path:
        path = Path(custom_path)
        if not path.exists():
            raise BinaryNotFoundError(f"ffmpeg not found at: {custom_path}")
        if not _is_executable(path):
            raise BinaryNotFoundError(f"ffmpeg is not executable: {custom_path}")
        return path

    # Try to find ffmpeg on PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return Path(ffmpeg_path)

    raise BinaryNotFoundError(
        "ffmpeg not found on PATH. Install with: brew install ffmpeg "
        "or specify path with --ffmpeg-bin",
    )


def check_ffmpeg_version(ffmpeg_path: Path) -> str:
    """Check ffmpeg version and capabilities.
    
    Args:
        ffmpeg_path: Path to ffmpeg binary
        
    Returns:
        Version string
        
    Raises:
        BinaryNotFoundError: If ffmpeg is not working or missing libmp3lame
    """
    try:
        result = subprocess.run(
            [str(ffmpeg_path), "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            raise BinaryNotFoundError(f"ffmpeg failed to run: {result.stderr}")

        # Check for libmp3lame support
        if "libmp3lame" not in result.stdout:
            raise BinaryNotFoundError(
                "ffmpeg found but libmp3lame codec not available. "
                "Install ffmpeg with: brew install ffmpeg",
            )

        # Extract version
        lines = result.stdout.split("\n")
        version_line = next((line for line in lines if line.startswith("ffmpeg version")), "")
        return version_line

    except subprocess.TimeoutExpired as e:
        raise BinaryNotFoundError(f"ffmpeg version check timed out: {e}") from e
    except FileNotFoundError as e:
        raise BinaryNotFoundError(f"ffmpeg not found: {e}") from e


def detect_permission_issue(dump_path: Path) -> bool:
    """Detect if permission issues prevent SystemAudioDump from running.
    
    Args:
        dump_path: Path to SystemAudioDump binary
        
    Returns:
        True if permission issue is detected
    """
    try:
        # Quick test run to check for permission issues
        result = subprocess.run(
            [str(dump_path)],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        # Look for permission-related error patterns
        stderr = result.stderr.lower()
        stdout = result.stdout.lower()

        permission_indicators = [
            "screen recording",
            "permission",
            "privacy",
            "security",
            "access",
            "denied",
        ]

        return any(
            indicator in stderr or indicator in stdout
            for indicator in permission_indicators
        )

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # If the binary doesn't respond quickly, it might be waiting for permission
        return True


def _is_executable(path: Path) -> bool:
    """Check if a file is executable.
    
    Args:
        path: Path to check
        
    Returns:
        True if file is executable
    """
    try:
        return path.stat().st_mode & 0o111 != 0
    except OSError:
        return False
