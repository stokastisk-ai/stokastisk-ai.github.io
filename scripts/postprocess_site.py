#!/usr/bin/env python3
"""Deterministic fix-ups applied to the built site before validation and deployment (stdlib only).

1. Publish the social card image at the site root.  Great Docs copies it into the Quarto project but Quarto
   does not carry an unreferenced file into _site, so og:image would 404 (verified on the pinned Great Docs commit).
2. Give every API reference page that Great Docs left with the site-wide fallback description its own factual
   description, built only from the object's name, kind and module (no invented behaviour).  Pages whose
   docstring supplies a summary are left untouched.  Unique descriptions are an SEO requirement.

Usage: python scripts/postprocess_site.py [--staged _src/stokastisk]
"""
from __future__ import annotations

import argparse
import html
from html import parser as html_parser
import json
import re
import shutil
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUFFIX = "in the Stokastisk Python SDK for vLLM on Kaggle dual Tesla T4 GPUs"


def kinds(inv: Path) -> dict[str, str]:
    raw = inv.read_bytes().split(b"\n", 4)[4]
    out = {}
    for line in zlib.decompress(raw).decode().splitlines():
        m = re.match(r"^(\S+)\s+(py:\w+)\s+-?\d+\s+(\S+)\s", line)
        if m:
            out[m.group(3)] = m.group(2)          # location -> role
    return out


class _Ids(html_parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("id", "name") and v:
                self.ids.add(v)


def fix_headings_and_anchors(site: Path) -> dict:
    """Deterministic repairs of Great Docs template output: one <h1> per page; no link fragments that point at ids the target page lacks."""
    pages = [p for p in site.rglob("*.html") if "site_libs" not in p.parts]
    texts = {p: p.read_text(encoding="utf-8") for p in pages}
    ids = {}
    for p, t in texts.items():
        q = _Ids(); q.feed(t); ids[p] = q.ids
    h1_pages = anchors = 0
    for p, t in texts.items():
        new = t
        n = {"open": 0}

        def h1(m):
            if m.group(1) == "":
                n["open"] += 1
                return m.group(0) if n["open"] == 1 else m.group(0).replace("<h1", "<h2", 1)
            return m.group(0) if n["open"] <= 1 else "</h2>"
        new = re.sub(r"<(/?)h1\b[^>]*>", h1, new)
        if n["open"] > 1:
            h1_pages += 1

        def link(m):
            nonlocal anchors
            href = m.group(2)
            if "#" not in href or re.match(r"^(https?:|mailto:|#)", href):
                return m.group(0)
            base, frag = href.split("#", 1)
            tgt = (p.parent / base).resolve() if base else p
            if tgt in ids and frag and frag not in ids[tgt] and not frag.startswith(("tab-", "section-", "fn", "ref-", "cb")):
                anchors += 1
                return f'{m.group(1)}{base or ""}{m.group(3)}' if base else m.group(0)
            return m.group(0)
        new = re.sub(r'(<a [^>]*?href=")([^"]*)(")', link, new)
        if new != t:
            p.write_text(new, encoding="utf-8")
    return {"h1_pages": h1_pages, "anchors": anchors}


def write_legacy_redirects(site: Path, cfg: str) -> int:
    """The project site used to live under /stokastisk-docs/. Write one tiny HTML redirect per page there (GitHub Pages cannot send 301s):
    canonical to the root URL, immediate meta refresh and a visible link. Not listed in the sitemap. Never touches /stokastisk/ (the SDK's project site)."""
    m = re.search(r"site_url:\s*(\S+)", cfg)
    base = m.group(1).rstrip("/") + "/"
    assert not (site / "stokastisk").exists(), "root site must not contain a /stokastisk/ namespace"
    n = 0
    for p in sorted(site.rglob("*.html")):
        rel = p.relative_to(site).as_posix()
        if "site_libs" in p.parts or rel in ("404.html",) or rel.startswith(("stokastisk-docs/", ".well-known/")):
            continue
        target = base + ("" if rel == "index.html" else rel)
        out = site / "stokastisk-docs" / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved: Stokastisk documentation</title>'
                       f'<link rel="canonical" href="{target}"><meta http-equiv="refresh" content="0; url={target}">'
                       f'<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
                       f'<body><p>This page moved to <a href="{target}">{target}</a>.</p></body></html>\n', encoding="utf-8")
        n += 1
    idx = site / "stokastisk-docs" / "index.html"
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", default=str(ROOT / "_src" / "stokastisk"))
    args = ap.parse_args()
    site = Path(args.staged) / "website" / "_site"
    build = Path(args.staged) / "website" / "_quarto" / "default"

    og = build / "og-image.png"
    if og.is_file():
        shutil.copy2(og, site / "og-image.png")

    # The homepage already carries the brand in its title; the "| Stokastisk" title template would repeat it.
    src = (Path(args.staged) / "website" / "index.qmd").read_text(encoding="utf-8")
    pt = re.search(r'^pagetitle:\s*"(.+)"\s*$', src, re.M)
    if pt:
        idx = site / "index.html"
        text = idx.read_text(encoding="utf-8")
        title = html.escape(pt.group(1), quote=False)
        text = re.sub(r"<title>.*?</title>", lambda m: f"<title>{title}</title>", text, count=1, flags=re.S)
        text = re.sub(r'(<meta (?:property|name)="(?:og|twitter):title" content=")[^"]*(")', lambda m: m.group(1) + html.escape(pt.group(1)) + m.group(2), text)
        idx.write_text(text, encoding="utf-8")

    cfg = (Path(args.staged) / "website" / "great-docs.yml").read_text(encoding="utf-8")
    m = re.search(r"default_description:\s*>-\n((?:\s+.+\n)+)", cfg)
    default = " ".join(l.strip() for l in m.group(1).splitlines()) if m else ""
    roles = kinds(site / "objects.inv")
    role_word = {"py:function": "function", "py:class": "class", "py:method": "method", "py:attribute": "attribute", "py:data": "constant",
                 "py:module": "module", "py:exception": "exception"}
    def norm(x: str) -> str:
        return html.unescape(x).replace("\u2019", "'").replace("\u2026", "").strip()

    explicit = {
        "license.html": "Apache-2.0 licence of the Stokastisk Python SDK, reproduced on its documentation site.",
        "changelog.html": "Release history of the Stokastisk Python SDK for vLLM on Kaggle dual Tesla T4 GPUs, generated from the GitHub releases.",
    }
    changed = 0
    pages = sorted((site / "reference").glob("*.html")) + [site / n for n in explicit if (site / n).is_file()]
    for page in pages:
        text = page.read_text(encoding="utf-8")
        m = re.search(r'<meta name="description" content="([^"]*)"', text)
        if not m or not default.startswith(norm(m.group(1))) or len(norm(m.group(1))) < 40:
            continue
        if page.name in explicit:
            desc = explicit[page.name]
        elif page.name == "index.html":
            desc = "Index of the generated Stokastisk API reference: the LLM engine, StokastiskConfig, serving, parallelism, topology, diagnostics, compatibility checks and exceptions."
        else:
            t = re.search(r"<title>(.*?)</title>", text, re.S).group(1).split(" | ")[0].strip()
            name = t.removesuffix("()")
            role = role_word.get(roles.get(f"reference/{page.name}", ""), "")
            if not role:
                role = "function" if t.endswith("()") else ("constant" if name.split(".")[-1].isupper() else "class")
            desc = f"API reference for {name}, a {role} {SUFFIX}: signature, parameters and a link to its source."
        esc = html.escape(desc, quote=True)
        text = text.replace(m.group(0), f'<meta name="description" content="{esc}"')
        text = re.sub(r'(<meta (?:property|name)="(?:og|twitter):description" content=")[^"]*(")', lambda mm: mm.group(1) + esc + mm.group(2), text)

        def ld(mm):
            return re.sub(r'("description":\s*)"(?:[^"\\]|\\.)*"', lambda d: d.group(1) + json.dumps(desc), mm.group(0), count=1)
        text = re.sub(r'<script type="application/ld\+json">.*?</script>', ld, text, flags=re.S)
        page.write_text(text, encoding="utf-8")
        changed += 1
    repaired = fix_headings_and_anchors(site)
    redirects = write_legacy_redirects(site, cfg)
    print(f"h1 demoted on {repaired['h1_pages']} pages; {repaired['anchors']} dangling fragments removed; {redirects} legacy redirect pages written")
    print(f"og-image published: {(site / 'og-image.png').is_file()}; descriptions made unique on {changed} pages")


if __name__ == "__main__":
    main()
