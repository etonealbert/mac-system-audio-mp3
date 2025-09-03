# SLI Recorder

A **typed**, minimal, reliable Python command-line tool that records **system audio (Mac speakers)** using [`systemAudioDump`](https://github.com/sohzm/systemAudioDump), and stops when the user presses **⌘+C (Ctrl+C)**, saving the recording as an **MP3** in a local `recordings/` folder.

> **Important**: This records **system audio only** (no microphone). It relies on macOS ScreenCaptureKit permissions—macOS will prompt the user the first time.

## Features

- **System audio recording** on macOS 13+ (Apple Silicon & Intel)
- **Automatic 2.5-hour cap** (9,000 seconds hard limit)
- **Graceful Ctrl+C handling** with proper MP3 finalization
- **Typed Python** with full `mypy` compatibility
- **Clean CLI** with `typer` for excellent UX
- **Binary auto-detection** for `SystemAudioDump` and `ffmpeg`
- **Permission detection** with helpful error messages

## Requirements

- **macOS 13+** (Apple Silicon or Intel)
- **Python 3.10+**
- **ffmpeg** (with libmp3lame support)
- **SystemAudioDump** binary (built from source)

## Installation

### 1. Install System Dependencies

```bash
# Install ffmpeg with MP3 support
brew install ffmpeg

# Install Xcode command line tools (if needed)
xcode-select --install
```

### 2. Build SystemAudioDump

```bash
# Add as git submodule
git submodule add https://github.com/sohzm/systemAudioDump externals/systemAudioDump

# Build the Swift binary
cd externals/systemAudioDump
swift build -c release
cd ../..

# Binary will be at: externals/systemAudioDump/.build/release/SystemAudioDump
```

### 3. Install SLI Recorder

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -U pip
pip install -e .

# Or install dependencies manually:
# pip install typer>=0.12.0 typing-extensions>=4.9.0
```

### 4. Grant Permissions (First Run)

On first run, macOS will prompt for **Screen Recording** permission. Grant access for your terminal application in:

**System Settings → Privacy & Security → Screen Recording**

## Usage

### Basic Recording

```bash
# Record with automatic filename
sli-recorder

# Record with title
sli-recorder "focus-music"

# Stop with Ctrl+C or auto-stops after 2.5 hours
```

### Advanced Options

```bash
# Custom output directory and bitrate
sli-recorder "meeting-audio" --outdir ~/Desktop/recordings --bitrate 128k

# Custom duration (1 hour)
sli-recorder --max-seconds 3600

# Specify binary paths
sli-recorder --dump-bin ./externals/systemAudioDump/.build/release/SystemAudioDump --ffmpeg-bin /usr/local/bin/ffmpeg

# Overwrite existing files
sli-recorder "test" --overwrite

# Verbose logging
sli-recorder --verbose

# Dry run (show commands without executing)
sli-recorder --dry-run
```

### Complete CLI Reference

```
sli-recorder [OPTIONS] [TITLE]

Arguments:
  TITLE                   Optional title for the recording

Options:
  --outdir PATH           Output directory for recordings [default: ./recordings]
  --bitrate TEXT          MP3 bitrate (e.g., '128k', '160k') [default: 160k]
  --max-seconds INTEGER   Hard cap in seconds (default 9000 = 2.5h) [default: 9000]
  --dump-bin PATH         Path to SystemAudioDump binary (autodetect if not specified)
  --ffmpeg-bin TEXT       Path to ffmpeg binary (default: 'ffmpeg' on PATH)
  --overwrite             Overwrite output if exists [default: False]
  --verbose               Show detailed logs [default: False]
  --dry-run               Print resolved commands without executing [default: False]
  --version               Show version and exit
  --help                  Show this message and exit
```

## Output Files

Recordings are saved as MP3 files in the `recordings/` directory with timestamps:

```
recordings/20250102-1430.mp3                    # No title
recordings/20250102-1430--focus-music.mp3       # With title
recordings/20250102-1430--team-meeting.mp3      # Sanitized title
```

## Audio Pipeline

The tool creates a pipeline between two processes:

1. **SystemAudioDump** → Raw PCM audio (16-bit, stereo, 24kHz) to stdout
2. **ffmpeg** → Encodes PCM from stdin to MP3 with libmp3lame

```bash
# Conceptual pipeline
SystemAudioDump | ffmpeg -f s16le -ar 24000 -ac 2 -i pipe:0 -c:a libmp3lame -b:a 160k -t 9000 output.mp3
```

## Development

### Code Quality

```bash
# Type checking
mypy sli_recorder/

# Linting and formatting
ruff check sli_recorder/
ruff format sli_recorder/

# Run both
ruff check --fix sli_recorder/ && mypy sli_recorder/
```

### Project Structure

```
sli_recorder/
├── __init__.py           # Package initialization
├── cli.py               # Typer CLI interface and main entry point
├── recorder.py          # Process orchestration and signal handling
├── types.py            # Type definitions and protocols
├── paths.py            # Path utilities and filename generation
├── detect.py           # Binary detection and permission checks
└── log.py              # Logging configuration
```

## Troubleshooting

### Permission Issues

If you see permission-related errors:

1. Go to **System Settings → Privacy & Security → Screen Recording**
2. Enable your terminal application (Terminal.app, iTerm2, etc.)
3. Restart your terminal and try again

### Binary Not Found

```bash
# Check if SystemAudioDump was built correctly
ls -la externals/systemAudioDump/.build/release/SystemAudioDump

# Check if ffmpeg is installed
ffmpeg -version | head -1

# Check for libmp3lame support
ffmpeg -codecs | grep mp3
```

### Common Issues

1. **"SystemAudioDump not found"** → Build the binary with `swift build -c release`
2. **"ffmpeg not found"** → Install with `brew install ffmpeg`
3. **"libmp3lame not available"** → Reinstall ffmpeg: `brew uninstall ffmpeg && brew install ffmpeg`
4. **Permission denied** → Grant Screen Recording permission in System Settings
5. **File exists error** → Use `--overwrite` flag or choose different title

## Technical Details

- **Audio format**: 16-bit PCM, stereo, 24kHz (SystemAudioDump output)
- **MP3 encoding**: libmp3lame, 160kbps default, VBR possible
- **Duration limit**: 9,000 seconds (2.5 hours) hard cap via ffmpeg `-t` option
- **Signal handling**: Graceful SIGINT/SIGTERM handling for clean MP3 finalization
- **Process management**: Parent process orchestrates child processes with proper cleanup

## License

This project structure and implementation are provided as-is. See individual component licenses:
- [SystemAudioDump](https://github.com/sohzm/systemAudioDump) for the audio capture component
- [FFmpeg](https://ffmpeg.org/) for the audio encoding component