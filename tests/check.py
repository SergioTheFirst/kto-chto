#!/usr/bin/env python3
"""Проверки собранного сайта: python build.py && python tests/check.py [--draft]

Устроено по образцу landing/tests/check.py проекта amanu (github.com/gsamat/amanu,
MIT): только наблюдаемое — метаданные, локальность ресурсов, доступность, ссылки,
sitemap. Плюс правила этого сайта: ни одного скрипта и счётчика, словарь запретов,
конкуренты не названы, цены только из site.json, пример помечен выдуманным.
--draft пропускает незаданную почту (для локального просмотра); выкладка — без него.
"""

import json
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
CFG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
BASE = CFG["base_url"].rstrip("/") + "/"
PREFIX = urlsplit(BASE).path or "/"
EMAIL = CFG["vars"]["email"]
BANNED = ("дословн", "досье", "для суда", "детектор лжи", "гарантируем точность", "vpn", "впн")
COMPETITORS = ("amanu", "svitok", "imot", "roistat")
PRICES = {unescape(v) for k, v in CFG["vars"].items() if k.startswith("price_")}
DRAFT = "--draft" in sys.argv

failures = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.h1 = 0
        self.title = ""
        self.meta = {}
        self.canonicals = []
        self.anchors = []
        self.resources = []
        self.imgs = []
        self.forms = 0
        self.scripts = 0
        self.handlers = 0
        self.styles = 0
        self.tabindex = 0
        self.text = []
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.handlers += sum(1 for k in a if k.startswith("on"))
        self.styles += "style" in a
        if (a.get("tabindex") or "0").lstrip("-").isdigit() and int(a.get("tabindex") or 0) > 0:
            self.tabindex += 1
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "h1":
            self.h1 += 1
        elif tag in ("title", "style"):
            self._in = tag
        elif tag == "meta" and (a.get("name") or a.get("property")):
            self.meta[a.get("name") or a.get("property")] = a.get("content") or ""
        elif tag == "link":
            rel = (a.get("rel") or "").split()
            if "canonical" in rel:
                self.canonicals.append(a.get("href"))
            else:
                self.resources.append(a.get("href") or "")
        elif tag == "a":
            self.anchors.append(a.get("href") or "")
        elif tag == "img":
            self.imgs.append(a)
            self.resources.append(a.get("src") or "")
        elif tag == "source":
            self.resources += [p.strip().split()[0] for p in (a.get("srcset") or "").split(",") if p.strip()]
        elif tag in ("script", "iframe", "object", "embed"):
            self.scripts += 1
            self.resources.append(a.get("src") or "")
        elif tag == "form":
            self.forms += 1

    def handle_endtag(self, tag):
        if tag == self._in:
            self._in = None

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in != "style":
            self.text.append(data)


def local_file(url):
    """Файл в _site, на который указывает ссылка своего сайта, или None для чужой."""
    s = urlsplit(url)
    if s.scheme or url.startswith("//"):
        if not url.startswith(BASE):
            return None
        path = urlsplit(url).path
    else:
        path = s.path
    if not path.startswith(PREFIX):
        return SITE / "__вне_сайта__" / path.lstrip("/")
    rel = unquote(path[len(PREFIX):])
    target = SITE / rel
    return target / "index.html" if rel == "" or rel.endswith("/") else target


def page_url(path):
    rel = path.relative_to(SITE).as_posix()
    return BASE + ("" if rel == "index.html" else rel[: -len("index.html")])


def main():
    check("сайт собран (_site есть)", SITE.is_dir())
    if not SITE.is_dir():
        return finish()
    check("почта для писем задана", DRAFT or not EMAIL.endswith(".invalid"), EMAIL)
    pages = sorted(p for p in SITE.rglob("index.html"))
    check("404.html есть", (SITE / "404.html").is_file())
    titles, descriptions = {}, {}

    for path in pages + [SITE / "404.html"]:
        p = Page()
        html = path.read_text(encoding="utf-8")
        p.feed(html)
        label = path.relative_to(SITE).as_posix()
        text = unescape(" ".join(p.text))
        low = " ".join([text, p.title, p.meta.get("description", "")]).lower()
        url = page_url(path) if path.name == "index.html" else None

        check(f"{label}: lang=ru", p.lang == "ru", str(p.lang))
        check(f"{label}: ровно один <h1>", p.h1 == 1, f"h1×{p.h1}")
        check(f"{label}: <title> есть", bool(p.title.strip()))
        check(f"{label}: description есть", bool(p.meta.get("description", "").strip()))
        check(f"{label}: нет незаменённых подстановок", "${" not in html)
        if url:
            titles.setdefault(p.title.strip(), []).append(label)
            descriptions.setdefault(p.meta.get("description", "").strip(), []).append(label)
            check(f"{label}: canonical = адрес страницы", p.canonicals == [url], str(p.canonicals))
            check(f"{label}: og:url = canonical", p.meta.get("og:url") == url)
        check(f"{label}: og:image своя и существует",
              p.meta.get("og:image") == BASE + "og.png" and (SITE / "og.png").is_file())
        check(f"{label}: ни одного скрипта/фрейма", p.scripts == 0)
        check(f"{label}: нет форм", p.forms == 0)
        check(f"{label}: нет on*-обработчиков и style=", p.handlers == 0 and p.styles == 0)
        check(f"{label}: нет tabindex > 0", p.tabindex == 0)
        check(f"{label}: у <img> есть alt, width, height",
              all({"alt", "width", "height"} <= set(i) for i in p.imgs))
        bad_res = [r for r in p.resources if not r or local_file(r) is None or not local_file(r).is_file()]
        check(f"{label}: ресурсы только свои и существуют", not bad_res, str(bad_res))
        broken = []
        for href in p.anchors:
            if href.startswith("mailto:"):
                if href[7:].split("?")[0] != EMAIL:
                    broken.append(href)
            elif href.startswith("#"):
                continue
            elif href.startswith("http://"):
                broken.append(href)
            else:
                target = local_file(href)
                if target is not None and not target.is_file():
                    broken.append(href)
        check(f"{label}: ссылки живые, https, почта одна", not broken, str(broken))
        words = [w for w in BANNED if w in low]
        check(f"{label}: словарь запретов чист", not words, str(words))
        named = [c for c in COMPETITORS if c in low]
        check(f"{label}: конкуренты не названы", not named, str(named))
        sums = set(re.findall(r"\d[\d  ]* ₽", text))
        check(f"{label}: цены только из site.json", sums <= PRICES, str(sums - PRICES))
        if "<mark>" in html or "ООО «Пример»" in text:
            check(f"{label}: пример помечен выдуманным", "выдуман" in text)

    for value, where in list(titles.items()) + list(descriptions.items()):
        check(f"уникально: «{value[:40]}…»", len(where) == 1, str(where))

    sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8") if (SITE / "sitemap.xml").is_file() else ""
    listed = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    check("sitemap.xml = все страницы", listed == {page_url(p) for p in pages},
          str(listed ^ {page_url(p) for p in pages}))
    robots = (SITE / "robots.txt").read_text(encoding="utf-8") if (SITE / "robots.txt").is_file() else ""
    check("robots.txt указывает sitemap", f"Sitemap: {BASE}sitemap.xml" in robots)

    css = (SITE / "style.css").read_text(encoding="utf-8")
    check("CSS: тёмная схема объявлена", "color-scheme: dark" in css)
    check("CSS: prefers-reduced-motion", "prefers-reduced-motion" in css)
    check("CSS: нет внешних url()/@import",
          not re.search(r"url\(\s*['\"]?(https?:)?//|@import", css))
    fonts = list((SITE / "fonts").glob("*.woff2"))
    check("шрифты с лицензией OFL рядом", not fonts or (SITE / "fonts" / "OFL.txt").is_file())
    return finish()


def finish():
    print()
    if failures:
        print(f"провалено: {len(failures)}")
        return 1
    print("все проверки прошли")
    return 0


if __name__ == "__main__":
    sys.exit(main())
