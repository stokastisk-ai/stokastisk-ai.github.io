#!/usr/bin/env python3
"""Stage the Stokastisk SDK at an immutable revision and overlay this repository's website/ sources.

The SDK repository stays authoritative for source, release metadata, evidence and generated references.
This repository owns the site configuration, hand-written guide pages and deployment.  Nothing is
installed or imported: staging is file copying only (no vLLM, no CUDA).

Usage:
    python scripts/stage_source.py                       # revision from SOURCE.lock.json, remote clone
    python scripts/stage_source.py --sdk-repo ../Project-Stokastisk   # local checkout (git archive)

Result: _src/stokastisk/ holding the SDK tree at the pinned commit, plus
  * src -> sdk                 (Great Docs only searches src/, python/ and lib/ for the package;
                                the staged copy gets a symlink, the SDK repository is not changed)
  * website/                   (this repository's website/ overlaid; generated pages added)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "SOURCE.lock.json"
SDK_URL = "https://github.com/stokastisk-ai/stokastisk"

# SDK Markdown page -> guide page, used to rewrite relative links inside generated pages
GUIDE_LINKS = {
    "getting-started.md": "installation.qmd", "configuration.md": "configuration.qmd", "engine.md": "engine.qmd",
    "structured-output.md": "structured-output.qmd", "server.md": "openai-server.qmd", "multi-gpu.md": "parallelism.qmd",
    "diagnostics.md": "diagnostics-compatibility.qmd", "errors.md": "errors-troubleshooting.qmd",
    "troubleshooting.md": "errors-troubleshooting.qmd", "feature-matrix.md": "feature-matrix.qmd",
    "advanced.md": "telemetry-benchmarking.qmd", "api-reference.md": "module-index.qmd",
}


def run(*cmd: str, cwd: Path | None = None) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def fetch(sdk_repo: str | None, rev: str, out: Path) -> None:
    out.mkdir(parents=True)
    if sdk_repo and Path(sdk_repo).is_dir():
        got = run("git", "-C", sdk_repo, "rev-parse", rev)
        if got != rev:
            sys.exit(f"revision {rev} does not resolve to itself in {sdk_repo} ({got})")
        archive = subprocess.run(["git", "-C", sdk_repo, "archive", rev], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(out)], input=archive, check=True)
    else:
        url = sdk_repo or SDK_URL
        run("git", "init", "-q", str(out))
        run("git", "-C", str(out), "fetch", "-q", "--depth", "1", url, rev)
        run("git", "-C", str(out), "-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD")
        got = run("git", "-C", str(out), "rev-parse", "HEAD")
        if got != rev:
            sys.exit(f"fetched {got}, expected {rev}")
        shutil.rmtree(out / ".git")                   # the staged tree is a snapshot, not a checkout


def rewrite_links(text: str, rev: str) -> str:
    def repl(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        base, _, frag = target.partition("#")
        name = base.rsplit("/", 1)[-1]
        if re.match(r"^(https?:|mailto:|#)", target):
            return m.group(0)
        if name in GUIDE_LINKS and "../" not in base.replace("../../", ""):
            return f"[{label}]({GUIDE_LINKS[name]}{'#' + frag if frag else ''})"
        rel = re.sub(r"^(\.\./|\./)+", "", base)
        if rel.startswith("guide/") and name in GUIDE_LINKS:
            return f"[{label}]({GUIDE_LINKS[name]})"
        if rel.startswith("docs/guide/") and name in GUIDE_LINKS:
            return f"[{label}]({GUIDE_LINKS[name]})"
        if rel in ("KAGGLE_ACCEPTANCE.md", "docs/KAGGLE_ACCEPTANCE.md"):
            return f"[{label}](kaggle-examples.qmd)"
        if rel in ("PRODUCTION_READINESS.md", "docs/PRODUCTION_READINESS.md"):
            return f"[{label}](production-limitations.qmd)"
        return f"[{label}]({SDK_URL}/blob/{rev}/{rel}{'#' + frag if frag else ''})"
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", repl, text)


def generated_page(src: Path, title: str, description: str, rev: str, note: str) -> str:
    body = src.read_text(encoding="utf-8")
    body = re.sub(r"\A# .*\n+", "", body)             # the page title comes from front matter
    body = rewrite_links(body, rev)
    return (f'---\ntitle: "{title}"\ndescription: "{description}"\n---\n\n'
            f"::: {{.callout-note}}\n{note}\n:::\n\n{body}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sdk-repo", help="local SDK checkout or alternative clone URL (default: the public repository)")
    ap.add_argument("--rev", help="40-hex SDK commit (default: SOURCE.lock.json)")
    ap.add_argument("--out", default=str(ROOT / "_src" / "stokastisk"))
    args = ap.parse_args()

    lock = json.loads(LOCK.read_text())
    rev = args.rev or lock["sdk"]["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", rev):
        sys.exit("the SDK revision must be a full 40-character commit SHA (immutable)")
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    fetch(args.sdk_repo, rev, out)

    if not (out / "sdk" / "stokastisk" / "__init__.py").is_file():
        sys.exit("staged tree has no sdk/stokastisk/__init__.py")
    (out / "src").symlink_to("sdk")

    shutil.copytree(ROOT / "website", out / "website", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("_site", "_quarto", ".quarto", "__pycache__"))
    cfg = out / "website" / "great-docs.yml"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("SDK_COMMIT", rev), encoding="utf-8")   # immutable source links
    ug = out / "website" / "user_guide"

    (ug / "feature-matrix.qmd").write_text(generated_page(
        out / "docs/guide/feature-matrix.md", "Feature matrix and verified models",
        "Which Stokastisk features and exact Hugging Face models were run on Kaggle dual Tesla T4 GPUs, and which are untested or unsupported.",
        rev, "Generated from `stokastisk.compat` (`FEATURES`, `MODEL_EVIDENCE`) in the SDK at the pinned source revision. "
             "Do not edit this table by hand; it is rebuilt on every site build."), encoding="utf-8")
    (ug / "module-index.qmd").write_text(generated_page(
        out / "docs/guide/api-reference.md", "Module index",
        "Every Python module of the stokastisk package with its public classes and functions, generated from source by the SDK's own docs builder.",
        rev, "Generated by the SDK's `scripts/release/build_docs_site.py` (AST based, nothing is imported). "
             "It lists every public name, including members that have no docstring and therefore have no page in the "
             "[API reference](../reference/index.html)."), encoding="utf-8")
    (out / "STAGED_FROM.json").write_text(json.dumps({"sdk_repository": SDK_URL, "commit": rev}, indent=1) + "\n")
    print(f"staged SDK {rev} -> {out}")


if __name__ == "__main__":
    main()
