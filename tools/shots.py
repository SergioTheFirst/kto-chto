#!/usr/bin/env python3
"""Снимки Chrome без окна (только стандартная библиотека + установленный Chrome/Edge).

    python tools/shots.py og     перерисовать site/static/og.png из tools/og.html
    python tools/shots.py        снимки всех страниц _site и 404 на 360/430/721/768/1440 и
                                 тёмной темы на 430 в _shots/ (для ревью вида)
"""

import functools
import http.server
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
OUT = ROOT / "_shots"
BROWSERS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]
WIDTHS = {360: 9000, 430: 9000, 721: 7000, 768: 7000, 1440: 5000}


def browser():
    for b in BROWSERS:
        if b.is_file():
            return str(b)
    sys.exit("нет Chrome или Edge")


MIN_WINDOW = 800   # окно Chrome уже ~500 px не сжимается — узкие ширины через iframe


def shot(url, out, width, height, dark=False):
    target = url
    if width < MIN_WINDOW:
        # /__wait держит запрос открытым: виртуальное время Chrome стоит, пока iframe
        # в реальном времени догружает и применяет шрифт (иначе снимок с запасным шрифтом)
        origin = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        harness = OUT / f"_frame-{width}.html"
        harness.write_text(
            f'<body style="margin:0"><img hidden alt="" src="{origin}/__wait">'
            f'<iframe src="{url}" width="{width}" height="{height}"'
            ' style="border:0;display:block"></iframe></body>', encoding="utf-8")
        target = harness.as_uri()
    cmd = [browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", f"--window-size={max(width, MIN_WINDOW)},{height}",
           "--virtual-time-budget=3000", f"--screenshot={out}", target]
    if dark:
        cmd.insert(2, "--force-dark-mode")
    subprocess.run(cmd, check=True, timeout=120, capture_output=True)
    if width < MIN_WINDOW:
        try:
            from PIL import Image  # необязательно: только обрезать пустое поле справа
            im = Image.open(out)
            im.load()
            cropped = im.crop((0, 0, width, height))
            im.close()
            cropped.save(out)
        except ImportError:
            pass


class Handler(http.server.SimpleHTTPRequestHandler):
    """Отдаёт _site под тем же префиксом пути, что и на GitHub Pages."""
    prefix = "/"

    def do_GET(self):
        if self.path == "/__wait":
            time.sleep(1.5)
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def translate_path(self, path):
        if path.startswith(self.prefix):
            path = "/" + path[len(self.prefix):]
        return super().translate_path(path)

    def log_message(self, *args):
        pass


def main():
    if sys.argv[1:] == ["og"]:
        shot((ROOT / "tools" / "og.html").as_uri(), ROOT / "site" / "static" / "og.png", 1200, 630)
        print("site/static/og.png")
        return
    cfg = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    Handler.prefix = urlsplit(cfg["base_url"]).path or "/"
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}{Handler.prefix}"
    OUT.mkdir(exist_ok=True)
    for page in sorted(SITE.rglob("index.html")) + [SITE / "404.html"]:
        rel = page.relative_to(SITE).as_posix().removesuffix("index.html")
        name = rel.strip("/").replace("/", "_").removesuffix(".html") or "index"
        url = base + rel
        for width, height in WIDTHS.items():
            shot(url, OUT / f"{name}-{width}.png", width, height)
        shot(url, OUT / f"{name}-430-dark.png", 430, WIDTHS[430], dark=True)
        print(name)
    server.shutdown()


if __name__ == "__main__":
    main()
