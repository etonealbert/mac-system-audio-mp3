"""Type definitions for SLI Recorder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class RecorderConfig:
    """Configuration for the audio recorder."""

    outdir: Path
    bitrate: str
    max_seconds: int
    dump_bin: Path
    ffmpeg_bin: Path
    overwrite: bool
    verbose: bool
    title: str | None


class ProcessProtocol(Protocol):
    """Protocol for subprocess-like objects."""

    def terminate(self) -> None:
        """Terminate the process."""
        ...

    def kill(self) -> None:
        """Kill the process."""
        ...

    def wait(self, timeout: float | None = None) -> int:
        """Wait for process to complete and return exit code."""
        ...

    @property
    def returncode(self) -> int | None:
        """Return code of the process, None if still running."""
        ...


class RecorderProtocol(Protocol):
    """Protocol for audio recorder implementations."""

    def start(self) -> None:
        """Start the recording process."""
        ...

    def stop_gracefully(self) -> None:
        """Stop recording gracefully, allowing processes to finalize output."""
        ...

    def wait(self) -> int:
        """Wait for recording to complete and return exit code."""
        ...

    @property
    def is_running(self) -> bool:
        """Check if recording is currently active."""
        ...
