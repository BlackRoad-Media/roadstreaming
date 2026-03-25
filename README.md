<!-- BlackRoad SEO Enhanced -->

# roadstreaming

> Part of **[BlackRoad OS](https://blackroad.io)** — Sovereign Computing for Everyone

[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-ff1d6c?style=for-the-badge)](https://blackroad.io)
[![BlackRoad Media](https://img.shields.io/badge/Org-BlackRoad-Media-2979ff?style=for-the-badge)](https://github.com/BlackRoad-Media)
[![License](https://img.shields.io/badge/License-Proprietary-f5a623?style=for-the-badge)](LICENSE)

**roadstreaming** is part of the **BlackRoad OS** ecosystem — a sovereign, distributed operating system built on edge computing, local AI, and mesh networking by **BlackRoad OS, Inc.**

## About BlackRoad OS

BlackRoad OS is a sovereign computing platform that runs AI locally on your own hardware. No cloud dependencies. No API keys. No surveillance. Built by [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc), a Delaware C-Corp founded in 2025.

### Key Features
- **Local AI** — Run LLMs on Raspberry Pi, Hailo-8, and commodity hardware
- **Mesh Networking** — WireGuard VPN, NATS pub/sub, peer-to-peer communication
- **Edge Computing** — 52 TOPS of AI acceleration across a Pi fleet
- **Self-Hosted Everything** — Git, DNS, storage, CI/CD, chat — all sovereign
- **Zero Cloud Dependencies** — Your data stays on your hardware

### The BlackRoad Ecosystem
| Organization | Focus |
|---|---|
| [BlackRoad OS](https://github.com/BlackRoad-OS) | Core platform and applications |
| [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc) | Corporate and enterprise |
| [BlackRoad AI](https://github.com/BlackRoad-AI) | Artificial intelligence and ML |
| [BlackRoad Hardware](https://github.com/BlackRoad-Hardware) | Edge hardware and IoT |
| [BlackRoad Security](https://github.com/BlackRoad-Security) | Cybersecurity and auditing |
| [BlackRoad Quantum](https://github.com/BlackRoad-Quantum) | Quantum computing research |
| [BlackRoad Agents](https://github.com/BlackRoad-Agents) | Autonomous AI agents |
| [BlackRoad Network](https://github.com/BlackRoad-Network) | Mesh and distributed networking |
| [BlackRoad Education](https://github.com/BlackRoad-Education) | Learning and tutoring platforms |
| [BlackRoad Labs](https://github.com/BlackRoad-Labs) | Research and experiments |
| [BlackRoad Cloud](https://github.com/BlackRoad-Cloud) | Self-hosted cloud infrastructure |
| [BlackRoad Forge](https://github.com/BlackRoad-Forge) | Developer tools and utilities |

### Links
- **Website**: [blackroad.io](https://blackroad.io)
- **Documentation**: [docs.blackroad.io](https://docs.blackroad.io)
- **Chat**: [chat.blackroad.io](https://chat.blackroad.io)
- **Search**: [search.blackroad.io](https://search.blackroad.io)

---


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
