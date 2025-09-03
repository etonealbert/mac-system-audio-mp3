"""Audio recording orchestration for SLI Recorder."""

from __future__ import annotations

import logging
import signal
import subprocess
import threading
import time
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Any

from .log import format_elapsed_time, log_command, log_process_result

if TYPE_CHECKING:
    from pathlib import Path
    
    from .types import RecorderConfig


class RecordingError(Exception):
    """Raised when recording fails."""


class Recorder:
    """Orchestrates SystemAudioDump and ffmpeg processes for recording."""

    def __init__(self, config: RecorderConfig, output_path: Path) -> None:
        """Initialize the recorder.
        
        Args:
            config: Recording configuration
            output_path: Path where the MP3 will be saved
        """
        self.config = config
        self.output_path = output_path
        self.logger = logging.getLogger("sli_recorder")

        self._dump_process: Popen[bytes] | None = None
        self._ffmpeg_process: Popen[bytes] | None = None
        self._start_time: float | None = None
        self._stop_requested = False
        self._status_thread: threading.Thread | None = None

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self) -> None:
        """Start the recording processes."""
        self.logger.info("Starting recording to: %s", self.output_path)
        self.logger.info("Recording will auto-stop after %d seconds (%.1f hours)",
                        self.config.max_seconds, self.config.max_seconds / 3600)
        self.logger.info("Press Ctrl+C to stop recording early")

        try:
            self._start_dump_process()
            self._start_ffmpeg_process()
            self._start_time = time.time()

            # Start status reporting thread
            if not self.config.verbose:
                self._status_thread = threading.Thread(target=self._status_reporter, daemon=True)
                self._status_thread.start()

        except Exception as e:
            self._cleanup_processes()
            raise RecordingError(f"Failed to start recording: {e}") from e

    def wait(self) -> int:
        """Wait for recording to complete and return exit code."""
        if not self._ffmpeg_process:
            raise RecordingError("Recording not started")

        try:
            # Wait for ffmpeg to complete (it will exit after max_seconds or on SIGINT)
            ffmpeg_code = self._ffmpeg_process.wait()

            # Clean up dump process
            if self._dump_process and self._dump_process.returncode is None:
                self._dump_process.terminate()
                try:
                    self._dump_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.debug("SystemAudioDump did not terminate gracefully, killing")
                    self._dump_process.kill()
                    self._dump_process.wait()

            # Log results
            if self._dump_process:
                log_process_result(
                    self.logger, "SystemAudioDump", self._dump_process.returncode or 0
                )
            log_process_result(self.logger, "ffmpeg", ffmpeg_code)

            # Determine stop reason
            elapsed = int(time.time() - (self._start_time or 0))
            if self._stop_requested:
                self.logger.info("Recording stopped by user after %s", format_elapsed_time(elapsed))
            else:
                self.logger.info("Recording completed after %s", format_elapsed_time(elapsed))

            # Check if output file was created
            if not self.output_path.exists():
                raise RecordingError("Output file was not created")

            file_size = self.output_path.stat().st_size
            self.logger.info("Saved %d bytes to: %s", file_size, self.output_path)

            return ffmpeg_code

        except Exception as e:
            self._cleanup_processes()
            raise RecordingError(f"Recording failed: {e}") from e

    def stop_gracefully(self) -> None:
        """Stop recording gracefully, allowing ffmpeg to finalize the MP3."""
        self._stop_requested = True

        # Send SIGINT to ffmpeg first to let it finalize the file
        if self._ffmpeg_process and self._ffmpeg_process.returncode is None:
            self.logger.debug("Sending SIGINT to ffmpeg for graceful shutdown")
            self._ffmpeg_process.send_signal(signal.SIGINT)

    @property
    def is_running(self) -> bool:
        """Check if recording is currently active."""
        return (
            self._ffmpeg_process is not None and
            self._ffmpeg_process.returncode is None
        )

    def _start_dump_process(self) -> None:
        """Start the SystemAudioDump process."""
        dump_cmd = [str(self.config.dump_bin)]
        log_command(self.logger, dump_cmd)

        self._dump_process = Popen(
            dump_cmd,
            stdout=PIPE,
            stderr=PIPE,
            text=False,  # Binary output
        )

        # Give it a moment to start and check for immediate failures
        time.sleep(0.1)
        if self._dump_process.poll() is not None:
            stderr = ""
            if self._dump_process.stderr:
                stderr = self._dump_process.stderr.read().decode("utf-8", errors="ignore")
            raise RecordingError(
                f"SystemAudioDump failed to start (exit code {self._dump_process.returncode}): {stderr}",
            )

    def _start_ffmpeg_process(self) -> None:
        """Start the ffmpeg process."""
        if not self._dump_process or not self._dump_process.stdout:
            raise RecordingError("Dump process not available")

        ffmpeg_cmd = [
            str(self.config.ffmpeg_bin),
            "-hide_banner",
            "-loglevel", "error",
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "2",
            "-i", "pipe:0",
            "-c:a", "libmp3lame",
            "-b:a", self.config.bitrate,
            "-vn",
            "-sn",
            "-t", str(self.config.max_seconds),
            str(self.output_path),
        ]
        log_command(self.logger, ffmpeg_cmd)

        self._ffmpeg_process = Popen(
            ffmpeg_cmd,
            stdin=self._dump_process.stdout,
            stdout=PIPE,
            stderr=PIPE,
            text=False,
        )

        # Close our reference to dump stdout so only ffmpeg has it
        self._dump_process.stdout.close()

        # Give it a moment to start
        time.sleep(0.1)
        if self._ffmpeg_process.poll() is not None:
            stderr = ""
            if self._ffmpeg_process.stderr:
                stderr = self._ffmpeg_process.stderr.read().decode("utf-8", errors="ignore")
            raise RecordingError(
                f"ffmpeg failed to start (exit code {self._ffmpeg_process.returncode}): {stderr}",
            )

    def _status_reporter(self) -> None:
        """Report recording status periodically."""
        if not self._start_time:
            return

        while self.is_running and not self._stop_requested:
            elapsed = int(time.time() - self._start_time)

            # Report every 30 seconds
            if elapsed > 0 and elapsed % 30 == 0:
                self.logger.info("%s recording… press Ctrl+C to stop", format_elapsed_time(elapsed))

            time.sleep(1)

    def _signal_handler(self, signum: int, _frame: Any) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        self.logger.debug("Received signal %d, stopping recording", signum)
        self.stop_gracefully()

    def _cleanup_processes(self) -> None:
        """Clean up any running processes."""
        for process, name in [
            (self._ffmpeg_process, "ffmpeg"),
            (self._dump_process, "SystemAudioDump"),
        ]:
            if process and process.returncode is None:
                self.logger.debug("Terminating %s", name)
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.debug("Killing %s after timeout", name)
                    process.kill()
                    process.wait()
                except Exception as e:
                    self.logger.debug("Error cleaning up %s: %s", name, e)
