#!/usr/bin/env python3
"""Validate the built Stokastisk documentation site (stdlib only, no network).

Checks, over every HTML page in <site>:
  canonical URL (exactly one, canonical host, matches the page's own path), unique <title> and meta description,
  no unintended noindex, one <h1>, valid JSON-LD, Open Graph / Twitter tags and an existing og:image,
  images have alt text, internal links / anchors / assets resolve, sitemap.xml <-> pages, robots.txt, llms.txt,
  python code blocks parse, install commands match RELEASE.json (current build + SHA256), no secrets / local paths.
Exit status 1 if any check fails.

Usage: python scripts/check_site.py [--site _src/stokastisk/website/_site] [--release _src/stokastisk/RELEASE.json]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://stokastisk-ai.github.io/"
PREFIX = urlparse(BASE).path            # "/"
SDK_NAMESPACE = ("/stokastisk/",)     # the SDK repository's own project site (package index, old guide): same host, not part of this build
LEGACY = "stokastisk-docs/"           # redirect pages for the former project-site URLs
SECRET_RE = re.compile(r"(hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|tokens\.env)")
LOCAL_RE = re.compile(r"(/media/waqasm86|/home/waqasm86|file:///|localhost:\d+/|127\.0\.0\.1:\d+/[a-z])")
NOINDEX_OK = {"404.html"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self._in_title = "", False
        self.meta, self.links, self.imgs, self.ids, self.hrefs, self.srcs = defaultdict(list), [], [], set(), [], []
        self.h1, self.jsonld, self._ld, self.code, self._code = 0, [], False, [], None
        self.canon = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key].append(a.get("content", ""))
        elif tag == "link":
            if a.get("rel") == "canonical":
                self.canon.append(a.get("href", ""))
            if a.get("href"):
                self.hrefs.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        elif tag in ("script", "img", "source") and a.get("src"):
            self.srcs.append(a["src"])
            if tag == "img":
                self.imgs.append(a)
        elif tag == "h1":
            self.h1 += 1
        if tag == "script" and a.get("type") == "application/ld+json":
            self._ld = True
            self.jsonld.append("")
        if tag == "code" and "sourceCode" in a.get("class", "") or (tag == "pre" and "sourceCode" in a.get("class", "")):
            self._code = ""
        if tag == "pre" and "python" in a.get("class", ""):
            self._code = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._ld = False
        if tag == "pre" and self._code is not None:
            self.code.append(self._code)
            self._code = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._ld:
            self.jsonld[-1] += data
        if self._code is not None:
            self._code += data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default=str(ROOT / "_src/stokastisk/website/_site"))
    ap.add_argument("--release", default=str(ROOT / "_src/stokastisk/RELEASE.json"))
    ap.add_argument("--report", default=str(ROOT / "reports/site-check.json"))
    args = ap.parse_args()
    site = Path(args.site)
    fails: list[str] = []
    warns: list[str] = []
    info: dict = {}

    def fail(msg):
        fails.append(msg)

    htmls = sorted(site.rglob("*.html"))
    redirects = [p for p in htmls if p.relative_to(site).as_posix().startswith(LEGACY)]
    htmls = [p for p in htmls if "site_libs" not in p.parts and "_extensions" not in p.parts and p not in redirects]
    pages = {}
    for p in htmls:
        pg = Page()
        pg.feed(p.read_text(encoding="utf-8", errors="replace"))
        pages[p] = pg
    info["html_pages"] = len(pages)

    titles, descs = defaultdict(list), defaultdict(list)
    multi_h1: list[str] = []
    indexable = {}
    for p, pg in pages.items():
        rel = p.relative_to(site).as_posix()
        robots = " ".join(pg.meta.get("robots", []))
        noindex = "noindex" in robots
        if noindex and rel not in NOINDEX_OK:
            warns.append(f"{rel}: noindex ({robots})")
        indexable[rel] = not noindex
        # canonical
        if rel in NOINDEX_OK or noindex:
            continue
        if len(pg.canon) != 1:
            fail(f"{rel}: {len(pg.canon)} canonical links")
        else:
            c = pg.canon[0]
            exp = BASE + ("" if rel == "index.html" else rel)
            if not c.startswith(BASE):
                fail(f"{rel}: canonical host/base is {c}")
            elif c not in (exp, BASE + rel.removesuffix("index.html")):
                fail(f"{rel}: canonical {c} != expected {exp}")
        t = pg.title.strip()
        d = (pg.meta.get("description") or [""])[0].strip()
        if not t:
            fail(f"{rel}: empty <title>")
        if not d:
            fail(f"{rel}: no meta description")
        titles[t].append(rel)
        descs[d].append(rel)
        if pg.h1 != 1:
            multi_h1.append(rel)
            fail(f"{rel}: {pg.h1} <h1> elements")
        for im in pg.imgs:
            if "alt" not in im:
                fail(f"{rel}: <img> without alt: {im.get('src')}")
        for k in ("og:title", "og:description", "og:url", "og:image", "twitter:card"):
            if not pg.meta.get(k):
                fail(f"{rel}: missing {k}")
        for ld in pg.jsonld:
            try:
                json.loads(ld)
            except Exception as e:
                fail(f"{rel}: invalid JSON-LD ({e})")
    info["pages_with_multiple_h1"] = len(multi_h1)
    for label, d in (("title", titles), ("description", descs)):
        for v, where in d.items():
            if len(where) > 1:
                fail(f"duplicate {label} on {len(where)} pages: {v[:70]!r} -> {', '.join(where[:4])}")
    info["unique_titles"], info["unique_descriptions"] = len(titles), len(descs)

    # og:image exists
    home = pages.get(site / "index.html")
    if home:
        for u in home.meta.get("og:image", []):
            path = urlparse(u).path.removeprefix(PREFIX)
            if not (site / path).is_file():
                fail(f"og:image does not exist in the site: {u}")

    # internal links, anchors, assets
    bad_links = 0
    bad_anchors: list = []
    for p, pg in pages.items():
        rel = p.relative_to(site).as_posix()
        for h in pg.hrefs + pg.srcs:
            if re.match(r"^(mailto:|tel:|javascript:|data:)", h) or h.startswith("#") and h == "#":
                continue
            u, frag = urldefrag(h)
            parsed = urlparse(u)
            if parsed.scheme in ("http", "https"):
                if parsed.netloc == urlparse(BASE).netloc and not parsed.path.startswith(SDK_NAMESPACE):
                    rel_p = parsed.path.removeprefix(PREFIX)
                    tp = site / rel_p
                    if tp.is_dir():
                        tp = tp / "index.html"
                    if rel_p and not tp.exists():
                        fail(f"{rel}: absolute internal link to missing file {h}")
                continue
            if not u:
                tgt = p
            else:
                tgt = (p.parent / unquote(parsed.path)).resolve()
                if tgt.is_dir():
                    tgt = tgt / "index.html"
            if not tgt.exists():
                bad_links += 1
                fail(f"{rel}: broken link {h}")
                continue
            if frag and tgt.suffix == ".html" and tgt in pages and frag not in pages[tgt].ids:
                if not frag.startswith(("tab-", "section-", "fn", "ref-", "cb")):
                    bad_anchors.append((rel, frag))
                    fail(f"{rel}: missing anchor #{frag} in {tgt.relative_to(site).as_posix()}")
    info["broken_internal_links"] = bad_links
    info["missing_anchors"] = len(bad_anchors)

    # namespace and legacy redirects
    if (site / "stokastisk").exists():
        fail("site contains a /stokastisk/ directory: that namespace belongs to the SDK repository's project site")
    bad_red = 0
    for r in redirects:
        t = r.read_text(encoding="utf-8")
        rel = r.relative_to(site).as_posix()[len(LEGACY):]
        tgt = BASE + ("" if rel == "index.html" else rel)
        if f'rel="canonical" href="{tgt}"' not in t or f'content="0; url={tgt}"' not in t or not (site / rel).is_file():
            bad_red += 1
            fail(f"legacy redirect wrong or without target: {rel}")
    info["legacy_redirect_pages"], info["legacy_redirect_errors"] = len(redirects), bad_red
    if not redirects:
        fail("no legacy /stokastisk-docs/ redirect pages were generated")
    # sitemap
    sm = site / "sitemap.xml"
    if not sm.is_file():
        fail("sitemap.xml missing")
    else:
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text for e in ET.parse(sm).getroot().findall("s:url/s:loc", ns)]
        info["sitemap_urls"] = len(locs)
        if len(set(locs)) != len(locs):
            fail("sitemap has duplicate URLs")
        mapped = set()
        for u in locs:
            if not u.startswith(BASE) or u.startswith(BASE + LEGACY) or u.startswith(BASE + "stokastisk/"):
                fail(f"sitemap URL outside the canonical docs namespace: {u}")
                continue
            rel = u[len(BASE):] or "index.html"
            if rel.endswith("/"):
                rel += "index.html"
            mapped.add(rel)
            if not (site / rel).is_file():
                fail(f"sitemap URL has no file: {u}")
        for rel, ok in indexable.items():
            if ok and rel not in NOINDEX_OK and rel not in mapped:
                warns.append(f"indexable page not in sitemap: {rel}")
    robots = site / "robots.txt"
    if not robots.is_file() or f"Sitemap: {BASE}sitemap.xml" not in robots.read_text():
        fail("robots.txt missing or lacks the sitemap line")
    elif re.search(r"^Disallow:\s*/\s*$", robots.read_text(), re.M):
        fail("robots.txt disallows the whole site")
    for f in ("llms.txt", "llms-full.txt"):
        if not (site / f).is_file():
            fail(f"{f} missing")

    # python code blocks parse
    blocks = bad_blocks = 0
    for p, pg in pages.items():
        rel_ = p.relative_to(site).as_posix()
        if rel_.startswith(("reference/", "user-guide/api-")) or rel_ in ("license.html", "changelog.html", "skills.html"):
            continue                      # generated signature blocks and non-Python files are not examples
        for code in pg.code:
            lines = [l for l in code.splitlines() if l.strip() and not l.lstrip().startswith(("!", "%"))]
            src = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith(("!", "%")))
            if not lines or ("import" not in src and "=" not in src and "(" not in src):
                continue
            if re.search(r"^\s*(\$|>>>|\.\.\.)", code, re.M) or code.lstrip().startswith(("# ", "[")) and "import" not in src:
                continue
            blocks += 1
            try:
                ast.parse(src)
            except SyntaxError:
                bad_blocks += 1
                warns.append(f"{p.relative_to(site).as_posix()}: python block does not parse: {src.strip().splitlines()[0][:60]!r}")
    info["python_blocks_parsed"], info["python_blocks_unparseable"] = blocks, bad_blocks

    # release consistency of install commands
    rel_json = json.loads(Path(args.release).read_text()) if Path(args.release).is_file() else None
    if rel_json:
        cur = rel_json["builds"][str(rel_json["current_build"])]
        withdrawn = {v["sha256"] for v in rel_json.get("withdrawn_builds", {}).values()}
        for p in htmls:
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"stokastisk @ (\S+?\.whl)#sha256=([0-9a-f]{64})", text):
                if m.group(1).rsplit("/", 1)[-1] != cur["filename"] or m.group(2) != cur["sha256"]:
                    fail(f"{p.relative_to(site).as_posix()}: install command is not the current build ({m.group(1)[-60:]})")
            for sha in withdrawn:
                if sha in text and "pip install" in text and f"#sha256={sha}" in text:
                    fail(f"{p.relative_to(site).as_posix()}: withdrawn build offered as install target")
        info["current_wheel"] = {"file": cur["filename"], "sha256": cur["sha256"]}

    # secrets / local paths in every published text file
    for f in site.rglob("*"):
        if f.is_file() and f.suffix in {".html", ".md", ".txt", ".xml", ".json", ".js", ".css", ".yml", ".yaml"} and "site_libs" not in f.parts:
            t = f.read_text(encoding="utf-8", errors="ignore")
            if SECRET_RE.search(t):
                fail(f"{f.relative_to(site).as_posix()}: matches a secret pattern (value not printed)")
            if LOCAL_RE.search(t):
                fail(f"{f.relative_to(site).as_posix()}: contains a local path or localhost URL")
    # private maintenance instructions must never be published as end-user skills or LLM context
    private = re.compile(r"stokastisk-docs-maintain|stokastisk-docs-seo|repair-publish|migrate-root|CLAUDE\.md|disable-model-invocation", re.I)
    skill_files = [site / "skills.html", site / "llms.txt", site / "llms-full.txt", *sorted((site / ".well-known").rglob("*"))] if (site / ".well-known").exists() else [site / "skills.html", site / "llms.txt", site / "llms-full.txt"]
    for f in skill_files:
        if f.is_file() and private.search(f.read_text(encoding="utf-8", errors="ignore")):
            fail(f"{f.relative_to(site).as_posix()}: mentions private maintenance instructions")
    info["agent_skill_files_checked"] = sum(1 for f in skill_files if f.is_file())
    forbidden = [f for f in site.rglob("*") if f.is_file() and f.suffix in {".whl", ".safetensors", ".bin", ".so", ".env", ".pt", ".gguf", ".zip"}]
    for f in forbidden:
        fail(f"forbidden binary/credential-type file published: {f.relative_to(site).as_posix()}")
    info["published_files"] = sum(1 for f in site.rglob("*") if f.is_file())

    out = {"failures": fails, "warnings": warns, "info": info}
    Path(args.report).parent.mkdir(exist_ok=True)
    Path(args.report).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(info, indent=1))
    for w in warns[:25]:
        print("WARN", w)
    for f in fails[:60]:
        print("FAIL", f)
    print(f"{len(fails)} failure(s), {len(warns)} warning(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
