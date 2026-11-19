#!/usr/bin/env python3.13
"""Generate the 'API details' guide pages from the SDK source (ast) plus website/api-notes.yml.

Every public module-level class, function, constant and every public method/property of the SDK gets a section with its signature,
parameter table (type, default, meaning), return value, exceptions raised in the body, docstring or site note, source link and
a documentation-status label. Sections carry explicit ids (#stokastisk.engine.LLM.generate) so cross-links resolve.
Usage: gen_api_details.py STAGED_DIR   (writes STAGED_DIR/website/user_guide/api-*.qmd)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_model import build_model, classify, load_notes  # noqa: E402

GROUPS = [
    ("api-engine-config", "API details: LLM engine and configuration", "Parameters, return values, exceptions and examples for stokastisk.LLM, StokastiskConfig and the package version constants.",
     ["stokastisk.engine", "stokastisk.config", "stokastisk._version", "stokastisk"]),
    ("api-errors", "API details: exceptions", "Every Stokastisk exception with its base class, constructor arguments and meaning.", ["stokastisk.errors"]),
    ("api-serving-structured", "API details: serving and structured output", "ServerProcess, the HTTP client helpers and the structured-output validators with parameters, errors and examples.",
     ["stokastisk.serving", "stokastisk.structured"]),
    ("api-parallel", "API details: parallelism, replicas and memory model", "ReplicaPool, the parallelism recommender, scheduler, routing, request queue and model memory estimator.", ["stokastisk.parallel"]),
    ("api-topology-limits", "API details: topology and Kaggle limits", "discover_topology, Topology, DeviceInfo, PeerAccess, PCIe classification and the Kaggle resource limit helpers.", ["stokastisk.topology", "stokastisk.limits"]),
    ("api-diagnostics-compat", "API details: diagnostics, compatibility and policy", "Environment validation, backend policy scanners, dependency profiles, model, dtype, quantization and feature checks.",
     ["stokastisk.diagnostics", "stokastisk.prohibited", "stokastisk.dependencies", "stokastisk.compat"]),
    ("api-telemetry", "API details: telemetry", "GPU sampling, statistics, segment timers and worker metrics.", ["stokastisk.telemetry"]),
    ("api-cuda-nccl-communication", "API details: CUDA, NCCL and communication", "CUDA device, stream, event and memory helpers, the NCCL self-test and the experimental host-staged transport.",
     ["stokastisk.cuda", "stokastisk.nccl", "stokastisk.communication"]),
    ("api-benchmarks", "API details: benchmarks", "Workloads, benchmark runners and report helpers for TP, PP, replicas and transports.", ["stokastisk.benchmarks"]),
]


def clean_doc(t: str) -> str:
    t = re.sub(r":\w+:`~?([^`]+)`", r"`\1`", t)
    t = t.replace("``", "`")
    return t


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def render_entry(key, e, note, sha, level) -> list[str]:
    status, missing = classify(e, note)
    h = "#" * level
    short = e["name"]
    anchor = key
    out = [f"{h} `{short}` {{#{anchor}}}", ""]
    src = f"https://github.com/stokastisk-ai/stokastisk/blob/{sha}/sdk/{key.rsplit('.', 1)[0].replace('.', '/') if e['kind'] in ('const',) else e['module'].replace('.', '/')}"
    src = f"https://github.com/stokastisk-ai/stokastisk/blob/{sha}/{e['file']}#L{e['line']}"
    label = {"complete": "documented", "partial": "partially documented", "internal": "internal helper (public by name only)"}[status]
    how = "source docstring" if e["doc"] else ("site note" if note and note.get("s") else "signature only")
    out.append(f"*{e['kind']}* · `{e['module']}` · [source]({src}){{.gd-no-link}} · status: **{label}** ({how})")
    out.append("")
    summary = clean_doc(e["doc"]) if e["doc"] else (note or {}).get("s", "")
    if summary:
        out += [summary if e["doc"] else summary + " *(site note; the released source has no docstring.)*", ""]
    if e["kind"] in ("class", "function", "method", "property"):
        args = ", ".join(f"{p['name']}{(': ' + p['annotation']) if p['annotation'] else ''}{(' = ' + p['default']) if p['default'] != '' else ''}" for p in e["params"] if e["kind"] != "class" or True)
        sig = f"{short}({args})" if e["kind"] != "property" else short
        if e["returns"]:
            sig += f" -> {e['returns']}"
        if e["kind"] == "class" and e["bases"]:
            sig = f"class {short}({', '.join(e['bases'])})" + (f"\n{short}({args})" if args else "")
        out += ["```python", sig, "```", ""]
    if e["kind"] == "const":
        out += [f"Value in source: `{(e.get('value') or '').replace(chr(10), ' ')[:160]}`", ""]
    pdesc = {k.lstrip("*"): v for k, v in (note or {}).get("p", {}).items()}
    if e["params"] and e["kind"] != "property":
        out += ["| Parameter | Type | Default | Meaning |", "|---|---|---|---|"]
        for p in e["params"]:
            n = p["name"].lstrip("*")
            out.append(f"| `{p['name']}` | `{esc(p['annotation']) or '-'}` | `{esc(p['default']) or '-'}` | {esc(pdesc.get(n, '')) or '-'} |")
        out.append("")
    if e["kind"] in ("function", "method", "property") and (e["returns"] or (note or {}).get("r")):
        out += [f"**Returns:** `{e['returns'] or '-'}`" + (f" - {note['r']}" if note and note.get("r") else ""), ""]
    xdesc = (note or {}).get("x", {})
    raises = list(dict.fromkeys(e["raises"] + list(xdesc)))
    if raises:
        out += ["**Raises:** " + "; ".join(f"`{r}`" + (f" ({xdesc[r]})" if r in xdesc else "") for r in raises), ""]
    if note and note.get("e"):
        out += ["**Example:**", "", "```python", note["e"].rstrip(), "```", ""]
    if note and note.get("rel"):
        out += ["**Related:** " + ", ".join(f"[`{r.replace('stokastisk.', '')}`]({PAGE_OF[r]}.qmd#{r})" if r in PAGE_OF else f"`{r}`" for r in note["rel"]), ""]
    return out


ALLKEYS: set = set()
PAGE_OF: dict = {}


def main() -> None:
    staged = Path(sys.argv[1])
    sha = (staged / "STAGED_FROM.json").read_text()
    sha = re.search(r'"commit":\s*"([0-9a-f]{40})"', sha).group(1)
    model = build_model(staged / "sdk" / "stokastisk")
    notes = load_notes(staged / "website" / "api-notes.yml")
    ALLKEYS.update(k for k in model)
    stale = [k for k in notes if k not in model]
    if stale:
        print("WARNING: notes for names that no longer exist:", ", ".join(stale))
    ug = staged / "website" / "user_guide"
    used = set()
    for slug, _t, _d, mods in GROUPS:                       # first pass: which page holds which object (for cross-page links)
        for k, e in model.items():
            if e["kind"] != "module" and any(e["module"] == m or (m != "stokastisk" and e["module"].startswith(m + ".")) for m in mods) and k not in PAGE_OF:
                PAGE_OF[k] = slug
    for slug, title, desc, mods in GROUPS:
        out = ["---", f'title: "{title}"', f'description: "{desc}"', 'guide-section: "API details"', "---", "",
               "::: {.callout-note}", "Generated from the pinned SDK source by static analysis (nothing is imported) and the site notes in `website/api-notes.yml`. "
               "Each section states whether its text is the source docstring or a site note. Objects marked *internal helper* are public by naming only and are not part of the supported user API. "
               "Sampling and engine arguments that come from vLLM are documented by vLLM; see the [API map](api-map.qmd).", ":::", ""]
        for m in mods:
            keys = [k for k, e in model.items() if (e["module"] == m or (m == "stokastisk" and e["module"] == "stokastisk")) and e["kind"] in ("class", "function", "const")]
            if m == "stokastisk.parallel":
                keys = [k for k, e in model.items() if e["module"].startswith("stokastisk.parallel") and e["kind"] in ("class", "function", "const")]
            elif m in ("stokastisk.topology", "stokastisk.telemetry", "stokastisk.cuda", "stokastisk.communication", "stokastisk.benchmarks"):
                keys = [k for k, e in model.items() if e["module"].startswith(m + ".") and e["kind"] in ("class", "function", "const")]
            if not keys:
                continue
            out += [f"## `{m}`", ""]
            if m in model and model[m]["doc"]:
                out += [clean_doc(model[m]["doc"]), ""]
            for k in keys:
                used.add(k)
                out += render_entry(k, model[k], notes.get(k), sha, 3)
                for mk, me in model.items():
                    if mk.startswith(k + ".") and me["kind"] in ("method", "property"):
                        used.add(mk)
                        out += render_entry(mk, me, notes.get(mk), sha, 4)
        (ug / f"{slug}.qmd").write_text("\n".join(out) + "\n", encoding="utf-8")
    left = [k for k, e in model.items() if e["kind"] != "module" and k not in used]
    print(f"wrote {len(GROUPS)} API detail pages covering {len(used)} objects; not placed: {len(left)} {left[:5]}")


if __name__ == "__main__":
    main()
