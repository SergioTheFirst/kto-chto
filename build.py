#!/usr/bin/env python3
"""Сборка сайта: site/pages/*.html + site/layout.html + site.json -> _site/.

Только стандартная библиотека. Страница — HTML-фрагмент с шапкой-комментарием:

    <!--
    title: Заголовок вкладки
    description: Описание для поиска
    -->
    <h1>...</h1> ...

Подстановки ${имя} берутся из site.json -> vars (цены, почта, название) и из
сборки (root, base, cta_href, cta_text). Неизвестное имя роняет сборку: число
на странице не может разойтись с источником.
"""

import json
import re
import shutil
import sys
from pathlib import Path
from string import Template
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "site"
OUT = ROOT / "_site"
META = re.compile(r"\A<!--\s*\n(.*?)\n-->\s*\n", re.S)
DASH = re.compile(r"(?<=\S) — ")   # тире не начинает строку: держится за слово перед ним


def load_page(path):
    text = path.read_text(encoding="utf-8")
    m = META.match(text)
    if not m:
        sys.exit(f"{path.name}: нет шапки <!-- title/description -->")
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            meta[key.strip()] = value.strip()
    return meta, text[m.end():]


def page_path(slug):
    """Адрес страницы относительно корня сайта: index -> '', ceny -> 'ceny/'."""
    return "" if slug == "index" else f"{slug}/"


def build_vars(cfg):
    base = cfg["base_url"].rstrip("/") + "/"
    v = dict(cfg["vars"])
    v["base"] = base
    v["root"] = urlsplit(base).path or "/"
    if cfg.get("preorder_url"):
        v["cta_href"], v["cta_text"] = cfg["preorder_url"], "Оформить предзаказ"
    else:
        subject = quote(f"{v['product']}: сообщите о выходе")
        v["cta_href"] = f"mailto:{v['email']}?subject={subject}"
        v["cta_text"] = "Сообщить мне о выходе"
    return v


def render(template, values, where):
    try:
        return Template(template).substitute(values)
    except (KeyError, ValueError) as exc:
        sys.exit(f"{where}: подстановка {exc}")


def main():
    cfg = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    v = build_vars(cfg)
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC / "static", OUT)

    urls = []
    for src in sorted((SRC / "pages").glob("*.html")):
        slug = src.stem
        meta, body = load_page(src)
        path = page_path(slug)
        values = {**v, "canonical": v["base"] + path}
        values["title"] = render(meta["title"], v, f"{src.name}: title")
        values["description"] = render(meta["description"], v, f"{src.name}: description")
        values["body"] = render(body, values, src.name)
        head, tag, rest = render(layout, values, f"layout для {src.name}").partition("<body")
        html = head + tag + DASH.sub("&nbsp;— ", rest)
        dest = OUT / "404.html" if slug == "404" else OUT / path / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        if slug != "404":
            urls.append(v["base"] + path)

    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {v['base']}sitemap.xml\n", encoding="utf-8")
    print(f"собрано страниц: {len(urls) + 1} -> {OUT}")


if __name__ == "__main__":
    main()
