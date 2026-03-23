#!/usr/bin/env python3
"""
CharFrame — Per-Character Frame Streaming
Each character is a frame. Text IS video.

Usage:
    python charframe.py "Hello world"
    python charframe.py --stdin < file.txt
    python charframe.py --ollama --model mistral "Explain gravity"
    python charframe.py --stream "pipe to ffplay" | ffplay -f rawvideo -pixel_format rgb24 -video_size 1280x720 -

Copyright (c) BlackRoad OS, Inc. All rights reserved.
"""

import argparse
import io
import json
import struct
import subprocess
import sys
import time
import urllib.request
import urllib.error

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow required. pip install pillow", file=sys.stderr)
    sys.exit(1)


# --- Constants ---
WIDTH = 1280
HEIGHT = 720
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
CURSOR_COLOR = (255, 29, 108)  # BlackRoad pink #FF1D6C
MARK_COLOR = (255, 29, 108)
STATUS_COLOR = (180, 180, 180)
FONT_SIZE = 20
LINE_HEIGHT = 24
COLS = 80
TOP_MARGIN = 40
LEFT_MARGIN = 40
STATUS_Y = HEIGHT - 36

DEMO_MESSAGE = (
    "CharFrame — Per-Character Frame Streaming\n"
    "\n"
    "Each character you see appeared as a single frame.\n"
    "At 30 fps, a 100-character sentence is 3.3 seconds of video.\n"
    "\n"
    "Text IS video. Typing as fast as thinking.\n"
    "\n"
    "Built by BlackRoad OS, Inc.\n"
    "Remember the Road. Pave Tomorrow."
)


def get_font(size=FONT_SIZE):
    """Load a monospace font, falling back to default."""
    mono_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFMono-Regular.otf",
        "/Library/Fonts/Courier New.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\cour.ttf",
    ]
    for path in mono_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except (OSError, IOError):
        return ImageFont.load_default()


def get_status_font():
    return get_font(14)


def word_wrap(text, cols=COLS):
    """Wrap text at column boundary, preserving explicit newlines."""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > cols:
            split = paragraph[:cols].rfind(" ")
            if split <= 0:
                split = cols
            lines.append(paragraph[:split])
            paragraph = paragraph[split:].lstrip(" ")
        lines.append(paragraph)
    return lines


class CharFrameRenderer:
    """Renders characters one-at-a-time into video frames."""

    def __init__(self, fps=30):
        self.fps = fps
        self.font = get_font()
        self.status_font = get_status_font()
        self.buffer = []  # list of characters received so far
        self.start_time = time.time()

    def render_frame(self, chars, total_expected=None, show_cursor=True):
        """Render current character buffer into a PIL Image."""
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # BlackRoad mark — small pink circle top-right
        mark_x, mark_y = WIDTH - 30, 14
        draw.ellipse([mark_x - 6, mark_y - 6, mark_x + 6, mark_y + 6], fill=MARK_COLOR)

        # Build the text from chars
        text = "".join(chars)
        lines = word_wrap(text, COLS)

        # Draw text lines
        cursor_pos = None
        char_idx = 0
        for row, line in enumerate(lines):
            y = TOP_MARGIN + row * LINE_HEIGHT
            if y > STATUS_Y - LINE_HEIGHT:
                break
            for col, ch in enumerate(line):
                x = LEFT_MARGIN + col * (FONT_SIZE * 0.6)
                draw.text((x, y), ch, fill=TEXT_COLOR, font=self.font)
                char_idx += 1
                cursor_pos = (x + FONT_SIZE * 0.6, y)
            # account for newline char
            char_idx += 1

        # If no text yet, cursor at origin
        if cursor_pos is None:
            cursor_pos = (LEFT_MARGIN, TOP_MARGIN)

        # Pink cursor block
        if show_cursor:
            cx, cy = cursor_pos
            draw.rectangle([cx, cy, cx + FONT_SIZE * 0.6, cy + LINE_HEIGHT], fill=CURSOR_COLOR)

        # Status bar
        elapsed = time.time() - self.start_time
        n = len(chars)
        cps = n / elapsed if elapsed > 0 else 0
        pct = (n / total_expected * 100) if total_expected and total_expected > 0 else 0
        status = f"frame {n}  |  {pct:.0f}%  |  {cps:.1f} chars/sec  |  {elapsed:.1f}s"
        draw.text((LEFT_MARGIN, STATUS_Y), status, fill=STATUS_COLOR, font=self.status_font)

        return img

    def image_to_raw(self, img):
        """Convert PIL Image to raw RGB bytes."""
        return img.tobytes()

    def image_to_jpeg(self, img, quality=85):
        """Convert PIL Image to JPEG bytes."""
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()


def stream_from_ollama(model, prompt):
    """Generator that yields tokens from a local Ollama instance."""
    url = "http://localhost:11434/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    token = obj.get("response", "")
                    if token:
                        yield token
                    if obj.get("done"):
                        return
                except json.JSONDecodeError:
                    continue
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach Ollama at {url}: {e}", file=sys.stderr)
        sys.exit(1)


def render_to_ffmpeg(chars_iter, total_chars, fps, output, renderer):
    """Pipe raw frames to ffmpeg to produce MP4."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pixel_format", "rgb24",
        "-video_size", f"{WIDTH}x{HEIGHT}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        output,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    chars = []
    for ch in chars_iter:
        chars.append(ch)
        frame = renderer.render_frame(chars, total_chars)
        raw = renderer.image_to_raw(frame)
        try:
            proc.stdin.write(raw)
        except BrokenPipeError:
            break

    # Hold final frame for 1 second
    if chars:
        final = renderer.render_frame(chars, total_chars, show_cursor=False)
        raw = renderer.image_to_raw(final)
        for _ in range(fps):
            try:
                proc.stdin.write(raw)
            except BrokenPipeError:
                break

    proc.stdin.close()
    proc.wait()
    n = len(chars)
    elapsed = time.time() - renderer.start_time
    print(f"Wrote {output}: {n} chars, {n + fps} frames, {elapsed:.1f}s", file=sys.stderr)


def render_to_stdout(chars_iter, total_chars, fps, renderer):
    """Write raw RGB frames to stdout for piping to ffplay."""
    chars = []
    frame_time = 1.0 / fps
    for ch in chars_iter:
        t0 = time.time()
        chars.append(ch)
        frame = renderer.render_frame(chars, total_chars)
        raw = renderer.image_to_raw(frame)
        try:
            sys.stdout.buffer.write(raw)
            sys.stdout.buffer.flush()
        except BrokenPipeError:
            break
        dt = time.time() - t0
        if dt < frame_time:
            time.sleep(frame_time - dt)


def char_iterator(text):
    """Yield one character at a time from a string."""
    for ch in text:
        yield ch


def token_char_iterator(token_iter):
    """Yield one character at a time from a token iterator."""
    for token in token_iter:
        for ch in token:
            yield ch


def main():
    parser = argparse.ArgumentParser(
        description="CharFrame: per-character frame streaming. Text IS video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  charframe.py 'Hello world'          Render to output.mp4\n"
               "  charframe.py --stdin < essay.txt     Read from pipe\n"
               "  charframe.py --ollama 'What is AI?'  Stream from Ollama\n"
               "  charframe.py --stream 'Hi' | ffplay  Raw frames to stdout\n",
    )
    parser.add_argument("text", nargs="*", help="Text to render (or demo if omitted)")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    parser.add_argument("--output", "-o", default="output.mp4", help="Output filename (default: output.mp4)")
    parser.add_argument("--stream", action="store_true", help="Raw frames to stdout (pipe to ffplay)")
    parser.add_argument("--stdin", action="store_true", help="Read text from stdin")
    parser.add_argument("--ollama", action="store_true", help="Stream from local Ollama model")
    parser.add_argument("--model", default="mistral", help="Ollama model name (default: mistral)")

    args = parser.parse_args()
    renderer = CharFrameRenderer(fps=args.fps)

    if args.ollama:
        prompt = " ".join(args.text) if args.text else "Tell me about BlackRoad OS in 3 sentences."
        print(f"Streaming from Ollama ({args.model}): {prompt[:60]}...", file=sys.stderr)
        token_gen = stream_from_ollama(args.model, prompt)
        chars_gen = token_char_iterator(token_gen)
        if args.stream:
            render_to_stdout(chars_gen, None, args.fps, renderer)
        else:
            render_to_ffmpeg(chars_gen, None, args.fps, args.output, renderer)
    elif args.stdin:
        text = sys.stdin.read()
        print(f"Read {len(text)} chars from stdin", file=sys.stderr)
        if args.stream:
            render_to_stdout(char_iterator(text), len(text), args.fps, renderer)
        else:
            render_to_ffmpeg(char_iterator(text), len(text), args.fps, args.output, renderer)
    elif args.text:
        text = " ".join(args.text)
        print(f"Rendering {len(text)} chars at {args.fps} fps", file=sys.stderr)
        if args.stream:
            render_to_stdout(char_iterator(text), len(text), args.fps, renderer)
        else:
            render_to_ffmpeg(char_iterator(text), len(text), args.fps, args.output, renderer)
    else:
        # Demo mode
        print(f"Demo mode: {len(DEMO_MESSAGE)} chars at {args.fps} fps", file=sys.stderr)
        if args.stream:
            render_to_stdout(char_iterator(DEMO_MESSAGE), len(DEMO_MESSAGE), args.fps, renderer)
        else:
            render_to_ffmpeg(char_iterator(DEMO_MESSAGE), len(DEMO_MESSAGE), args.fps, args.output, renderer)


if __name__ == "__main__":
    main()
