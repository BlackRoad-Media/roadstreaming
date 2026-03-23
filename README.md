# RoadStreaming -- Per-Character Frame Streaming

Each character is a frame. Typing as fast as thinking.

Text IS video. A 100-character sentence = 3.3 seconds of movie at 30 fps.
A full LLM response streams as a film you watch being written.

## How It Works

CharFrame renders every character of text into its own video frame.
Black background, white monospace text, pink cursor advancing one
character at a time. A status bar tracks frame count, progress,
characters per second, and elapsed time.

The result: text that plays like a movie. You watch the words appear
at exactly the speed they were produced -- whether typed, piped, or
streamed from an LLM.

## CLI Usage

```bash
# Render text to MP4 (each char = 1 frame at 30fps)
python charframe.py "Hello world"

# Demo mode (built-in message)
python charframe.py

# Read from stdin
echo "Some text" | python charframe.py --stdin

# Stream from Ollama (each token rendered char-by-char)
python charframe.py --ollama "Explain gravity in 3 sentences"
python charframe.py --ollama --model llama3 "What is BlackRoad?"

# Raw frames to stdout (pipe to ffplay for live preview)
python charframe.py --stream "Watch this" | \
  ffplay -f rawvideo -pixel_format rgb24 -video_size 1280x720 -

# Custom FPS and output filename
python charframe.py --fps 24 --output demo.mp4 "Slower render"
```

## Live Server

CharFrame Live serves an MJPEG stream over HTTP. Open a browser,
type a prompt, and watch the LLM response render frame-by-frame.

```bash
# Start the server
python charframe-live.py

# Start on a custom port
python charframe-live.py --port 9000 --fps 24
```

Endpoints:

| Path | Description |
|------|-------------|
| `/` | Web UI with prompt input |
| `/mjpeg?prompt=...` | MJPEG stream of CharFrame output |
| `/health` | JSON health check |

The MJPEG stream works in any browser -- no JavaScript required for
the video itself. The final frame holds for 3 seconds after the
response completes.

## Requirements

- Python 3.10+
- Pillow (`pip install pillow`)
- ffmpeg (for MP4 output in CLI mode)
- Ollama (optional, for LLM streaming)

```bash
pip install -r requirements.txt
```

## Frame Specs

| Property | Value |
|----------|-------|
| Resolution | 1280 x 720 |
| Background | Black (#000000) |
| Text | White, monospace |
| Cursor | Pink (#FF1D6C) |
| Columns | 80 |
| Default FPS | 30 |
| Format (CLI) | H.264 MP4 via ffmpeg |
| Format (Live) | MJPEG over HTTP |

## License

Proprietary -- BlackRoad OS, Inc. All rights reserved.
