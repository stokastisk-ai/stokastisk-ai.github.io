#!/usr/bin/env python3
"""API coverage audit: reconcile the SDK's public API with what the built site documents.

Pure static analysis (ast + the site's objects.inv). Nothing from stokastisk, vLLM or CUDA is imported.

Inputs (all under the staged tree, default _src/stokastisk):
  sdk/stokastisk/**/*.py              the source of truth
  docs/guide/api-reference.md         the SDK's own generated module index (must list every public def)
  website/_site/objects.inv           Great Docs' inventory of every documented object
  website/user_guide/*.qmd, index.qmd hand-written pages: every `stokastisk.X` they cite must exist

Outputs: reports/api-coverage.json and reports/api-coverage.md. Exit status 1 if there is a gap.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from api_model import build_model, classify, load_notes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Public names that are data tables or regular expressions rather than callable API. They have no
# page of their own; they are still listed in the module index (api-reference.md). Each needs a reason.
OMIT_REASON = {
    "const": "module-level constant or data table; listed in the module index, not given its own page",
}
OMIT_NAMES = {
    "stokastisk.benchmarks.baseline.TOPIC_WORDS", "stokastisk.benchmarks.baseline.SHORT", "stokastisk.benchmarks.baseline.LONG", "stokastisk.benchmarks.baseline.SCALING", "stokastisk.benchmarks.communication.SIZES",
    "stokastisk.communication.transport_registry.TRANSPORTS", "stokastisk.config.ALLOWED_ATTENTION_BACKENDS",
    "stokastisk.config.FORBIDDEN_ATTENTION_MARKERS", "stokastisk.config.ALLOWED_STRUCTURED_OUTPUT_BACKENDS",
    "stokastisk.config.EXECUTION_STRATEGIES", "stokastisk.config.EXPERIMENTAL_STRATEGIES", "stokastisk.config.MAX_GPUS",
    "stokastisk.config.NCCL_ENV_NO_P2P", "stokastisk.config.VLLM_ENV_NO_FLASHINFER", "stokastisk.compat.SM75",
    "stokastisk.compat.UNSUPPORTED_ARCHITECTURE_MARKERS", "stokastisk.compat.STUB_MODULE", "stokastisk.diagnostics.NATIVE_EXTENSIONS",
    "stokastisk.diagnostics.FLASH_NATIVE_MODULES", "stokastisk.diagnostics.PROHIBITED_DISTS", "stokastisk.diagnostics.PROHIBITED_MODULES",
    "stokastisk.nccl.SCHEMA_VERSION", "stokastisk.parallel.memory.UNSUPPORTED_ARCH_MARKERS",
    "stokastisk.parallel.memory.CUDA_CONTEXT_OVERHEAD_MIB", "stokastisk.parallel.recommender.WORKLOADS", "stokastisk.prohibited.STEM_RE",
    "stokastisk.prohibited.EXACT_STEMS", "stokastisk.prohibited.FA_PREFIX_RE", "stokastisk.prohibited.ALLOWED_FLASH_NAMED",
    "stokastisk.prohibited.BINARY_SUFFIXES", "stokastisk.prohibited.NATIVE_MARKERS", "stokastisk.prohibited.BINDING_RE",
    "stokastisk.prohibited.REFERENCE_RE", "stokastisk.prohibited.BLOCKED_IMPORT_NAMES", "stokastisk.prohibited.PROHIBITED_DISTS",
    "stokastisk.serving.SERVER_REQUIREMENTS", "stokastisk.topology.pcie.SYSFS_PCI",
}
# helpers used only by other modules / worker processes; public by naming, internal by purpose
INTERNAL_HELPERS = {
    "stokastisk.parallel.routing.effective_speed", "stokastisk.parallel.routing.projected_load", "stokastisk.parallel.worker.gpu_identity",
    "stokastisk.topology.pcie.pcie_sysfs", "stokastisk.topology.nvml.nvml_devices", "stokastisk.topology.nvml.smi_query",
    "stokastisk.topology.nvml.smi_topo_matrix", "stokastisk.topology.gpu_capabilities.torch_devices",
    "stokastisk.topology.gpu_capabilities.cuda_python_version", "stokastisk.parallel.scheduler.Decision",
}
UPSTREAM = {"SamplingParams": "vLLM class re-exported lazily from the bundled vLLM 0.25.1; documented upstream, not by this site"}


def read_inventory(path: Path) -> set[str]:
    """Names in a Sphinx objects.inv (v2)."""
    raw = path.read_bytes()
    body = raw.split(b"\n", 4)[4]
    names = set()
    for line in zlib.decompress(body).decode().splitlines():
        m = re.match(r"^(\S+)\s+\S+\s+-?\d+\s+\S+\s+.*$", line)
        if m:
            names.add(m.group(1))
    return names


def public_inventory(pkg: Path):
    """{dotted name: kind} for module-level public defs/classes/constants, plus class methods."""
    inv, methods, modules = {}, {}, set()
    for p in sorted(pkg.rglob("*.py")):
        mod = ".".join(("stokastisk",) + p.relative_to(pkg).with_suffix("").parts).replace(".__init__", "")
        modules.add(mod)
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_"):
                inv[f"{mod}.{n.name}"] = "function"
            elif isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
                inv[f"{mod}.{n.name}"] = "class"
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_"):
                        methods[f"{mod}.{n.name}.{m.name}"] = bool(ast.get_docstring(m))
            elif isinstance(n, (ast.Assign, ast.AnnAssign)) and not mod.endswith("_version"):
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, ast.Name) and not t.id.startswith("_") and t.id != "log":
                        inv[f"{mod}.{t.id}"] = "const"
    return inv, methods, modules


def top_level_exports(init: Path):
    """(__all__ list, {name: defining module} for eager and lazy re-exports)."""
    tree = ast.parse(init.read_text(encoding="utf-8"))
    names, origin = [], {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets):
            names = [e.value for e in n.value.elts]
        if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module:
            for a in n.names:
                origin[a.asname or a.name] = f"stokastisk.{n.module}"
    # lazy exports in __getattr__
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.level and n.module:
            for a in n.names:
                origin.setdefault(a.name, f"stokastisk.{n.module}")
        if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module is None:
            for a in n.names:
                origin.setdefault(a.name, f"stokastisk.{a.name}")
    return names, origin


def fix_origin(names, origin, inv):
    """Lazy exports are fetched with getattr(module, name); resolve them to their unique definition."""
    by_short = {}
    for dotted in inv:
        by_short.setdefault(dotted.rsplit(".", 1)[1], []).append(dotted.rsplit(".", 1)[0])
    for e in names:
        mods = by_short.get(e, [])
        if origin.get(e) is None or origin[e] not in mods:
            if len(mods) == 1:
                origin[e] = mods[0]
    return origin


def module_index_names(md: Path):
    """{module: set(names)} from the SDK's generated api-reference.md."""
    out, cur = {}, None
    for line in md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## `([\w.]+)`", line)
        if m:
            cur = m.group(1)
            out[cur] = set()
        elif cur and (m := re.match(r"^\| <code>(?:class|def)\s+(?:&nbsp;)*([\w.]+)", line)):
            out[cur].add(m.group(1).split("(")[0].split(".")[0])
        elif cur and (m := re.match(r"^\| <code>(?:&nbsp;)*([A-Za-z_]\w*)", line)):
            out[cur].add(m.group(1))
    return out


def cited_symbols(files):
    """`stokastisk.a.b.c` strings and `from stokastisk.x import a, b` names cited in hand-written pages."""
    cites = {}
    for f in files:
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\bstokastisk((?:\.[A-Za-z_]\w*)+)", text):
            if re.search(r"\.(whl|qmd|html|json|py)$", m.group(1)) or "__" in m.group(1):
                continue
            cites.setdefault(f.name, set()).add("stokastisk" + m.group(1))
        for m in re.finditer(r"from (stokastisk(?:\.\w+)*) import ([\w, ]+)", text):
            for n in [x.strip() for x in m.group(2).split(",") if x.strip()]:
                cites.setdefault(f.name, set()).add(f"{m.group(1)}.{n}")
    return cites


def resolve(sym, inv, methods, modules, exports, origin):
    if sym in modules or sym in inv or sym in methods:
        return True
    parts = sym.split(".")
    if len(parts) == 2 and parts[1] in exports:                      # stokastisk.LLM, stokastisk.SamplingParams
        return True
    if len(parts) >= 3 and parts[1] in origin:                        # stokastisk.LLM.chat via the re-export
        return f"{origin[parts[1]]}.{'.'.join(parts[1:])}" in (set(inv) | set(methods)) or f"{origin[parts[1]]}.{'.'.join(parts[1:])}" in inv
    if len(parts) >= 3 and ".".join(parts[:-1]) in modules:           # module attribute (constant) not tracked
        return False
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", default=str(ROOT / "_src" / "stokastisk"))
    ap.add_argument("--reports", default=str(ROOT / "reports"))
    args = ap.parse_args()
    st, rep = Path(args.staged), Path(args.reports)
    rep.mkdir(exist_ok=True)

    pkg = st / "sdk" / "stokastisk"
    inv, methods, modules = public_inventory(pkg)
    exports, origin = top_level_exports(pkg / "__init__.py")
    origin = fix_origin(exports, origin, inv)
    documented = read_inventory(st / "website" / "_site" / "objects.inv")
    mod_index = module_index_names(st / "docs" / "guide" / "api-reference.md")

    def has_page(dotted: str) -> bool:
        return dotted in documented

    status = {}
    for name, kind in inv.items():
        mod, short = name.rsplit(".", 1)
        top = [e for e in exports if origin.get(e) == mod and e == short]
        pages = [name] + [f"stokastisk.{short}"] * bool(top)
        if any(has_page(p) for p in pages):
            status[name] = "documented"
        elif name in OMIT_NAMES:
            status[name] = "omitted:data-table"
        elif name in INTERNAL_HELPERS:
            status[name] = "omitted:internal-helper"
        elif short in mod_index.get(mod, set()):
            status[name] = "module-index-only"      # no docstring: Great Docs skips undocumented objects; the SDK's own index lists it
        else:
            status[name] = "GAP"
    # __all__ reconciliation
    all_rows = []
    for e in exports:
        if e in UPSTREAM:
            all_rows.append((e, "upstream", UPSTREAM[e] + "; explained in user-guide/api-map.html"))
        elif e == "__version__":
            all_rows.append((e, "documented", "hand-written: user-guide/api-map.html#version-attributes and api-engine-config (stokastisk._version)"))
        else:
            d = origin.get(e, "stokastisk")
            full = f"{d}.{e}"
            ok = has_page(f"stokastisk.{e}") or has_page(full)
            idx = e in mod_index.get(d, set())
            all_rows.append((e, "documented" if ok else ("module-index-only" if idx else "GAP"), full))
    # methods of documented classes
    meth_rows = {"documented": 0, "no-docstring (module index only)": 0}
    for m, has_doc in methods.items():
        cls = m.rsplit(".", 1)[0]
        if status.get(cls) == "documented":
            meth_rows["documented" if has_page(m) or has_page(m.replace(cls, f"stokastisk.{cls.rsplit('.', 1)[1]}")) else "no-docstring (module index only)"] += 1
    # existing generated reference
    idx_gaps = []
    for name, kind in inv.items():
        mod, short = name.rsplit(".", 1)
        if kind != "const" and short not in mod_index.get(mod, set()):
            idx_gaps.append(name)
    # hand-written pages cite only real symbols
    guide = list((st / "website" / "user_guide").glob("*.qmd")) + [st / "website" / "index.qmd"]
    bad_cites = []
    model_keys = set(build_model(pkg))
    for f, syms in cited_symbols([g for g in guide if g.exists()]).items():
        for s in sorted(syms):
            parts_ = s.split('.')
            lazy_ok = len(parts_) >= 3 and any(k.startswith('.'.join(parts_[:-1]) + '.') or (k.rsplit('.', 1)[1] == parts_[-1] and k.rsplit('.', 1)[0].startswith('.'.join(parts_[:-1]))) for k in model_keys)
            if s not in model_keys and not lazy_ok and not resolve(s, inv, methods, modules, set(exports), origin):
                parts = s.split(".")
                # allow attribute chains on documented classes/functions and bare module attributes; flag unknown first segments
                tail_ok = len(parts) > 1 and ((".".join(parts[:2]) in modules) or parts[1] in exports or parts[1] in {m.split(".")[1] for m in modules if "." in m})
                if not tail_ok:
                    bad_cites.append((f, s))
                elif len(parts) >= 3 and ".".join(parts[:2]) in modules and f"{'.'.join(parts[:2])}.{parts[2]}" not in inv and ".".join(parts[:3]) not in modules:
                    bad_cites.append((f, s))

    # --- documentation depth: complete vs partial vs index-only, per object (detail pages + site notes) ---
    model = build_model(pkg)
    notes = load_notes(st / "website" / "api-notes.yml")
    detail_ids = set()
    for pg in (st / "website" / "_site" / "user-guide").glob("api-*.html"):
        detail_ids |= set(re.findall(r'id="([^"]+)"', pg.read_text(encoding="utf-8")))
    depth = {"complete": [], "partial": [], "internal": [], "no_detail_section": []}
    by_kind = {}
    for k, e in model.items():
        if e["kind"] == "module":
            continue
        cls, miss = classify(e, notes.get(k))
        if k not in detail_ids:
            depth["no_detail_section"].append(k)
        depth[cls].append(k if not miss else f"{k} [{', '.join(miss)}]")
        by_kind.setdefault(e["kind"], {}).setdefault(cls, 0)
        by_kind[e["kind"]][cls] += 1
    bad_src = [k for k, e in model.items() if e["kind"] != "module" and not ((st / e["file"]).is_file() and e["line"] <= len((st / e["file"]).read_text(encoding="utf-8").splitlines()))]
    stale_notes = sorted(n for n in notes if n not in model)
    gaps = [n for n, s in status.items() if s == "GAP"] + [e for e, s, _ in all_rows if s == "GAP"]
    summary = {
        "public_module_level_names": len(inv),
        "documented_with_own_page": sum(1 for s in status.values() if s == "documented"),
        "module_index_only_no_docstring": sum(1 for s in status.values() if s == "module-index-only"),
        "omitted_data_tables": sum(1 for s in status.values() if s == "omitted:data-table"),
        "omitted_internal_helpers": sum(1 for s in status.values() if s == "omitted:internal-helper"),
        "gaps": sorted(set(gaps)),
        "all_exports": len(exports),
        "all_exports_documented": sum(1 for _, s, _ in all_rows if s == "documented"),
        "all_exports_module_index_only": [e for e, s, _ in all_rows if s == "module-index-only"],
        "all_exports_upstream_or_omitted": [e for e, s, _ in all_rows if s in ("upstream", "omitted")],
        "public_methods_on_documented_classes": meth_rows,
        "missing_from_sdk_module_index": sorted(idx_gaps),
        "guide_citations_that_do_not_resolve": sorted(set(bad_cites)),
        "reference_objects_in_inventory": len(documented),
        "depth_total_objects": sum(len(v) for k, v in depth.items() if k != "no_detail_section"),
        "depth_complete": len(depth["complete"]),
        "depth_partial": depth["partial"],
        "depth_internal_justified": len(depth["internal"]),
        "depth_without_detail_section": depth["no_detail_section"],
        "depth_by_kind": by_kind,
        "stale_site_notes": stale_notes,
        "source_links_invalid": bad_src,
        "baseline_2026_11_19": {"public_module_level_names": 203, "own_great_docs_page": 137, "module_index_only": 26, "omitted_data_tables": 36, "omitted_internal_helpers": 4,
                                 "top_level_exports_documented": "49 of 51", "class_methods_documented": 18, "class_methods_index_only": 29},
    }
    (rep / "api-coverage.json").write_text(json.dumps(summary, indent=1) + "\n")
    lines = ["# API coverage report", "",
             "Static analysis of `sdk/stokastisk` (AST) against the built site's `objects.inv` and the SDK's own generated `docs/guide/api-reference.md`.", "",
             "| Measure | Result |", "|---|---|"]
    for k, v in summary.items():
        if k in ("depth_partial", "source_links_invalid", "depth_without_detail_section", "stale_site_notes", "gaps", "missing_from_sdk_module_index", "guide_citations_that_do_not_resolve", "all_exports_upstream_or_omitted", "all_exports_module_index_only"):
            lines.append(f"| {k} | {len(v)} {('→ ' + ', '.join(map(str, v))) if v else ''} |")
        else:
            lines.append(f"| {k} | {v} |")
    lines += ["", "## `stokastisk.__all__`", "", "| Name | Result | Page or reason |", "|---|---|---|"]
    lines += [f"| `{e}` | {s} | `{d}` |" for e, s, d in all_rows]
    (rep / "api-coverage.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[4:20]))
    sys.exit(1 if (gaps or idx_gaps or bad_cites or bad_src or depth['partial'] or depth['no_detail_section'] or stale_notes) else 0)


if __name__ == "__main__":
    main()
