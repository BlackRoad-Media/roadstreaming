#!/usr/bin/env python3
"""
CharFrame Live — HTTP server for live MJPEG character streaming.

Serves a UI at / with a prompt input box.
/mjpeg?prompt=... streams MJPEG frames from Ollama, one char per frame.
/health returns server status.

Copyright (c) BlackRoad OS, Inc. All rights reserved.
"""

import io
import json
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow required. pip install pillow")
    raise SystemExit(1)


# --- Config ---
HOST = "0.0.0.0"
PORT = 8800
WIDTH = 1280
HEIGHT = 720
FPS = 30
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "mistral"

BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
CURSOR_COLOR = (255, 29, 108)
MARK_COLOR = (255, 29, 108)
STATUS_COLOR = (180, 180, 180)
FONT_SIZE = 20
LINE_HEIGHT = 24
COLS = 80
TOP_MARGIN = 40
LEFT_MARGIN = 40
STATUS_Y = HEIGHT - 36

HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CharFrame Live</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0a0a0a;
    color: #e0e0e0;
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
    padding: 24px;
  }
  h1 {
    font-size: 1.4rem;
    font-weight: 600;
    margin-bottom: 8px;
    color: #fff;
  }
  .subtitle {
    font-size: 0.85rem;
    color: #888;
    margin-bottom: 20px;
  }
  .input-row {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    width: 100%;
    max-width: 720px;
  }
  input[type="text"] {
    flex: 1;
    padding: 10px 14px;
    font-size: 1rem;
    font-family: inherit;
    background: #1a1a1a;
    color: #fff;
    border: 1px solid #333;
    border-radius: 6px;
    outline: none;
  }
  input[type="text"]:focus {
    border-color: #ff1d6c;
  }
  button {
    padding: 10px 20px;
    font-size: 1rem;
    font-family: inherit;
    background: #ff1d6c;
    color: #fff;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
  }
  button:hover { background: #e0185f; }
  .viewer {
    border: 1px solid #222;
    border-radius: 8px;
    overflow: hidden;
    background: #000;
  }
  img#stream {
    display: block;
    width: 100%;
    max-width: 960px;
    height: auto;
  }
  .footer {
    margin-top: 16px;
    font-size: 0.75rem;
    color: #555;
  }
</style>
</head>
<body>
  <h1>CharFrame Live</h1>
  <p class="subtitle">Each character is a frame. Text IS video.</p>
  <div class="input-row">
    <input type="text" id="prompt" placeholder="Ask anything..." autofocus>
    <button onclick="go()">Stream</button>
  </div>
  <div class="viewer">
    <img id="stream" src="" alt="stream will appear here">
  </div>
  <p class="footer">BlackRoad OS, Inc. | RoadStreaming</p>
  <script>
    function go() {
      const p = document.getElementById('prompt').value.trim();
      if (!p) return;
      const img = document.getElementById('stream');
      img.src = '/mjpeg?prompt=' + encodeURIComponent(p) + '&t=' + Date.now();
    }
    document.getElementById('prompt').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') go();
    });
  </script>
</body>
</html>"""


def get_font(size=FONT_SIZE):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFMono-Regular.otf",
        "/Library/Fonts/Courier New.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


FONT = get_font(FONT_SIZE)
FONT_SMALL = get_font(14)


def word_wrap(text, cols=COLS):
    lines = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        while len(para) > cols:
            sp = para[:cols].rfind(" ")
            if sp <= 0:
                sp = cols
            lines.append(para[:sp])
            para = para[sp:].lstrip(" ")
        lines.append(para)
    return lines


def render_frame(chars, total_expected=None, start_time=None, show_cursor=True):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Pink mark
    mx, my = WIDTH - 30, 14
    draw.ellipse([mx - 6, my - 6, mx + 6, my + 6], fill=MARK_COLOR)

    text = "".join(chars)
    lines = word_wrap(text, COLS)

    cursor_pos = None
    for row, line in enumerate(lines):
        y = TOP_MARGIN + row * LINE_HEIGHT
        if y > STATUS_Y - LINE_HEIGHT:
            break
        for col, ch in enumerate(line):
            x = LEFT_MARGIN + col * (FONT_SIZE * 0.6)
            draw.text((x, y), ch, fill=TEXT_COLOR, font=FONT)
            cursor_pos = (x + FONT_SIZE * 0.6, y)

    if cursor_pos is None:
        cursor_pos = (LEFT_MARGIN, TOP_MARGIN)

    if show_cursor:
        cx, cy = cursor_pos
        draw.rectangle([cx, cy, cx + FONT_SIZE * 0.6, cy + LINE_HEIGHT], fill=CURSOR_COLOR)

    # Status bar
    elapsed = (time.time() - start_time) if start_time else 0
    n = len(chars)
    cps = n / elapsed if elapsed > 0 else 0
    pct = (n / total_expected * 100) if total_expected and total_expected > 0 else 0
    status = f"frame {n}  |  {pct:.0f}%  |  {cps:.1f} chars/sec  |  {elapsed:.1f}s"
    draw.text((LEFT_MARGIN, STATUS_Y), status, fill=STATUS_COLOR, font=FONT_SMALL)

    return img


def image_to_jpeg(img, quality=80):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def stream_ollama_tokens(model, prompt):
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
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
    except urllib.error.URLError:
        yield "[Ollama unreachable]"


BOUNDARY = b"--charframe"


class CharFrameHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *a):
        # quiet logging
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_UI.encode())

        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "service": "charframe-live",
                "fps": FPS,
            }).encode())

        elif path == "/mjpeg":
            qs = parse_qs(parsed.query)
            prompt = qs.get("prompt", ["Tell me about BlackRoad OS."])[0]
            model = qs.get("model", [DEFAULT_MODEL])[0]

            self.send_response(200)
            self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary=charframe")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Pragma", "no-cache")
            self.end_headers()

            frame_time = 1.0 / FPS
            chars = []
            start = time.time()

            try:
                for token in stream_ollama_tokens(model, prompt):
                    for ch in token:
                        t0 = time.time()
                        chars.append(ch)
                        img = render_frame(chars, None, start, show_cursor=True)
                        jpeg = image_to_jpeg(img)

                        self.wfile.write(BOUNDARY + b"\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpeg)}\r\n".encode())
                        self.wfile.write(b"\r\n")
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()

                        dt = time.time() - t0
                        if dt < frame_time:
                            time.sleep(frame_time - dt)

                # Hold final frame for 3 seconds
                if chars:
                    final_img = render_frame(chars, None, start, show_cursor=False)
                    jpeg = image_to_jpeg(final_img)
                    hold_frames = FPS * 3
                    for _ in range(hold_frames):
                        t0 = time.time()
                        self.wfile.write(BOUNDARY + b"\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpeg)}\r\n".encode())
                        self.wfile.write(b"\r\n")
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                        dt = time.time() - t0
                        if dt < frame_time:
                            time.sleep(frame_time - dt)

            except (BrokenPipeError, ConnectionResetError):
                pass

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CharFrame Live MJPEG server")
    parser.add_argument("--host", default=HOST, help=f"Bind address (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    parser.add_argument("--fps", type=int, default=FPS, help=f"Frames per second (default: {FPS})")
    args = parser.parse_args()

    fps = args.fps

    server = HTTPServer((args.host, args.port), CharFrameHandler)
    server.fps = fps
    print(f"CharFrame Live running at http://{args.host}:{args.port}")
    print(f"  UI:     http://localhost:{args.port}/")
    print(f"  MJPEG:  http://localhost:{args.port}/mjpeg?prompt=...")
    print(f"  Health: http://localhost:{args.port}/health")
    print(f"  FPS:    {fps}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
