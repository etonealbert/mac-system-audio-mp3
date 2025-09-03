"""Command-line interface for SLI Recorder."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .detect import (
    BinaryNotFoundError,
    check_ffmpeg_version,
    detect_permission_issue,
    find_ffmpeg,
    find_system_audio_dump,
)
from .log import setup_logging
from .paths import build_output_filename, check_output_file, ensure_output_dir
from .recorder import Recorder, RecordingError
from .types import RecorderConfig

app = typer.Typer(
    name="sli-recorder",
    help="Minimal typed Python CLI tool for recording macOS system audio to MP3",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"sli-recorder {__version__}")
        raise typer.Exit()


@app.command()
def main(
    title: Annotated[str | None, typer.Argument(help="Optional title for the recording")] = None,
    outdir: Annotated[
        Path,
        typer.Option(
            "--outdir",
            help="Output directory for recordings",
            file_okay=False,
            dir_okay=True,
        ),
    ] = Path("./recordings"),
    bitrate: Annotated[
        str,
        typer.Option("--bitrate", help="MP3 bitrate (e.g., '128k', '160k')"),
    ] = "160k",
    max_seconds: Annotated[
        int,
        typer.Option("--max-seconds", help="Hard cap in seconds (default 9000 = 2.5h)"),
    ] = 9000,
    dump_bin: Annotated[
        Path | None,
        typer.Option(
            "--dump-bin",
            help="Path to SystemAudioDump binary (autodetect if not specified)",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ] = None,
    ffmpeg_bin: Annotated[
        str | None,
        typer.Option("--ffmpeg-bin", help="Path to ffmpeg binary (default: 'ffmpeg' on PATH)"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite output if exists"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed logs"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print resolved commands without executing"),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, help="Show version and exit"),
    ] = None,
) -> None:
    """Record system audio to MP3 using SystemAudioDump and ffmpeg.
    
    Records macOS system audio (speakers, not microphone) and saves as MP3.
    Stops when user presses Ctrl+C or after max-seconds timeout.
    
    Examples:
        sli-recorder "focus-music"
        sli-recorder --bitrate 128k --max-seconds 3600
        sli-recorder --dump-bin ./SystemAudioDump --verbose
    """
    # Set up logging
    logger = setup_logging(verbose=verbose)

    try:
        # Validate max_seconds
        if max_seconds < 10:
            logger.warning("Max duration is very short (%d seconds)", max_seconds)

        # Find binaries
        try:
            dump_path = find_system_audio_dump(dump_bin)
            ffmpeg_path = find_ffmpeg(ffmpeg_bin)
        except BinaryNotFoundError as e:
            logger.error(str(e))
            raise typer.Exit(1) from e

        # Check ffmpeg capabilities
        try:
            ffmpeg_version = check_ffmpeg_version(ffmpeg_path)
            logger.debug("Found %s", ffmpeg_version.split("\n")[0])
        except BinaryNotFoundError as e:
            logger.error(str(e))
            raise typer.Exit(1) from e

        # Check for permission issues
        if detect_permission_issue(dump_path):
            logger.error(
                "macOS requires Screen Recording permission for system audio. "
                "Grant access for your terminal in System Settings → Privacy & Security → "
                "Screen Recording, then re-run.",
            )
            raise typer.Exit(1)

        # Set up output paths
        ensure_output_dir(outdir)
        filename = build_output_filename(title)
        output_path = outdir / filename

        try:
            check_output_file(output_path, overwrite=overwrite)
        except FileExistsError as e:
            logger.error(str(e))
            raise typer.Exit(1) from e

        # Create configuration
        config = RecorderConfig(
            outdir=outdir,
            bitrate=bitrate,
            max_seconds=max_seconds,
            dump_bin=dump_path,
            ffmpeg_bin=ffmpeg_path,
            overwrite=overwrite,
            verbose=verbose,
            title=title,
        )

        # Dry run mode
        if dry_run:
            _print_dry_run(config, output_path)
            return

        # Start recording
        recorder = Recorder(config, output_path)
        recorder.start()
        exit_code = recorder.wait()

        if exit_code != 0:
            logger.error("Recording failed with exit code %d", exit_code)
            raise typer.Exit(exit_code)

    except RecordingError as e:
        logger.error(str(e))
        raise typer.Exit(1) from e
    except KeyboardInterrupt:
        # This should be handled by the recorder's signal handler
        logger.debug("KeyboardInterrupt caught in main")
        raise typer.Exit(130)  # 128 + SIGINT(2)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        if verbose:
            import traceback
            logger.error("Traceback:\n%s", traceback.format_exc())
        raise typer.Exit(1) from e


def _print_dry_run(config: RecorderConfig, output_path: Path) -> None:
    """Print the commands that would be executed in dry-run mode."""
    typer.echo("Dry run mode - commands that would be executed:")
    typer.echo("")
    typer.echo(f"Output file: {output_path}")
    typer.echo(f"Max duration: {config.max_seconds} seconds ({config.max_seconds / 3600:.1f} hours)")
    typer.echo("")
    typer.echo("SystemAudioDump command:")
    typer.echo(f"  {config.dump_bin}")
    typer.echo("")
    typer.echo("ffmpeg command:")
    ffmpeg_cmd = [
        str(config.ffmpeg_bin),
        "-hide_banner",
        "-loglevel", "error",
        "-f", "s16le",
        "-ar", "24000",
        "-ac", "2",
        "-i", "pipe:0",
        "-c:a", "libmp3lame",
        "-b:a", config.bitrate,
        "-vn",
        "-sn",
        "-t", str(config.max_seconds),
        str(output_path),
    ]
    typer.echo(f"  {' '.join(ffmpeg_cmd)}")
    typer.echo("")
    typer.echo("Pipeline:")
    typer.echo(f"  {config.dump_bin} | {' '.join(ffmpeg_cmd)}")


if __name__ == "__main__":
    app()
