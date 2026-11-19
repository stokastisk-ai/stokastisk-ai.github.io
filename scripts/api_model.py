#!/usr/bin/env python3.13
"""Static API model of the Stokastisk SDK (ast only; nothing is imported or executed).

build_model(pkg_dir) -> {dotted name: entry}. Entry keys: kind (class|function|method|property|const),
module, name, params [{name, annotation, default, kind}], returns, raises [exception names raised directly in the body],
doc (full docstring or ""), line, bases, fields (dataclass / annotated class attributes), decorators.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _u(node) -> str:
    return ast.unparse(node) if node is not None else ""


def _params(args: ast.arguments, skip_self=False):
    out = []
    pos = args.posonlyargs + args.args
    defaults = [None] * (len(pos) - len(args.defaults)) + list(args.defaults)
    for a, d in zip(pos, defaults):
        out.append({"name": a.arg, "annotation": _u(a.annotation), "default": _u(d), "kind": "positional"})
    if args.vararg:
        out.append({"name": "*" + args.vararg.arg, "annotation": _u(args.vararg.annotation), "default": "", "kind": "var"})
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        out.append({"name": a.arg, "annotation": _u(a.annotation), "default": _u(d), "kind": "keyword-only"})
    if args.kwarg:
        out.append({"name": "**" + args.kwarg.arg, "annotation": _u(args.kwarg.annotation), "default": "", "kind": "var"})
    if skip_self and out and out[0]["name"] in ("self", "cls"):
        out = out[1:]
    return out


def _raises(fn) -> list[str]:
    names = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Raise) and n.exc is not None:
            e = n.exc.func if isinstance(n.exc, ast.Call) else n.exc
            s = _u(e)
            if s and s[0].isupper() and s not in names:
                names.append(s)
    return names


def _entry(node, mod, qual, kind, line_src=None, method=False):
    return {
        "kind": kind, "module": mod, "name": qual, "line": node.lineno,
        "params": _params(node.args, skip_self=method) if hasattr(node, "args") else [],
        "returns": _u(node.returns) if hasattr(node, "returns") else "",
        "raises": _raises(node) if hasattr(node, "args") else [],
        "doc": ast.get_docstring(node) or "",
        "decorators": [_u(d) for d in getattr(node, "decorator_list", [])],
        "bases": [_u(b) for b in getattr(node, "bases", [])],
        "fields": [],
    }


def build_model(pkg: Path) -> dict:
    model = {}
    files = {}
    for p in sorted(pkg.rglob("*.py")):
        mod = ".".join(("stokastisk",) + p.relative_to(pkg).with_suffix("").parts).replace(".__init__", "")
        files[mod] = "sdk/stokastisk/" + p.relative_to(pkg).as_posix()
        tree = ast.parse(p.read_text(encoding="utf-8"))
        if mod != "stokastisk" and ast.get_docstring(tree):
            model[mod] = {"kind": "module", "module": mod, "name": mod, "doc": ast.get_docstring(tree), "line": 1, "params": [], "returns": "", "raises": [], "decorators": [], "bases": [], "fields": []}
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_"):
                model[f"{mod}.{n.name}"] = _entry(n, mod, n.name, "function")
            elif isinstance(n, ast.ClassDef) and not n.name.startswith("_"):
                e = _entry(n, mod, n.name, "class")
                init = next((m for m in n.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"), None)
                if init is not None:
                    e["params"] = _params(init.args, skip_self=True)
                    e["raises"] = _raises(init)
                for m in n.body:
                    if isinstance(m, ast.AnnAssign) and isinstance(m.target, ast.Name) and not m.target.id.startswith("_"):
                        e["fields"].append({"name": m.target.id, "annotation": _u(m.annotation), "default": _u(m.value)})
                model[f"{mod}.{n.name}"] = e
                if init is None and e["fields"]:
                    e["params"] = [{"name": f["name"], "annotation": f["annotation"], "default": f["default"], "kind": "field"} for f in e["fields"]]
                for m in n.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_"):
                        decs = [_u(d) for d in m.decorator_list]
                        kind = "property" if "property" in decs else "method"
                        model[f"{mod}.{n.name}.{m.name}"] = _entry(m, mod, f"{n.name}.{m.name}", kind, method=True)
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in targets:
                    if isinstance(t, ast.Name) and not t.id.startswith("_") and t.id != "log":
                        e = {"kind": "const", "module": mod, "name": t.id, "line": n.lineno, "params": [], "returns": _u(getattr(n, "annotation", None)),
                             "raises": [], "doc": "", "decorators": [], "bases": [], "fields": [], "value": _u(n.value)[:200]}
                        model[f"{mod}.{t.id}"] = e
    for e in model.values():
        e["file"] = files.get(e["module"], "")
    return model


if __name__ == "__main__":
    import sys
    m = build_model(Path(sys.argv[1]))
    for k, e in m.items():
        sig = ", ".join(f"{p['name']}{(':' + p['annotation']) if p['annotation'] else ''}{('=' + p['default']) if p['default'] else ''}" for p in e["params"])
        print(f"{e['kind'][:4]} {k} ({sig}) -> {e['returns']} | R:{','.join(e['raises'])} | D:{e['doc'].splitlines()[0][:70] if e['doc'] else '-'}")


def load_notes(path: Path) -> dict:
    """Load api-notes.yml plus any api-notes-*.yml beside it; later files extend (p and x dicts are merged) earlier ones."""
    import yaml
    out: dict = {}
    for f in [path, *sorted(path.parent.glob(path.stem + "-*.yml"))]:
        for k, v in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).items():
            cur = out.setdefault(k, {})
            for fk, fv in v.items():
                if isinstance(fv, dict) and isinstance(cur.get(fk), dict):
                    cur[fk].update(fv)
                else:
                    cur[fk] = fv
    return out


def classify(entry: dict, note: dict | None) -> tuple[str, list[str]]:
    """('complete'|'partial'|'internal'|'module', missing) for one entry. Complete = has a summary (docstring or site note) and every
    parameter is explained (note text, or named in the docstring) and a return is described or annotated."""
    note = note or {}
    if entry["kind"] == "module":
        return "module", []
    if note.get("status") == "internal":
        return "internal", []
    missing = []
    if not (entry["doc"] or note.get("s")):
        missing.append("summary")
    pdesc = {k.lstrip("*"): v for k, v in note.get("p", {}).items()}
    for p in entry["params"]:
        n = p["name"].lstrip("*")
        if p["name"].startswith("*") and not p["name"].startswith("**") or entry["kind"] == "const":
            continue
        if n not in pdesc and n not in entry["doc"]:
            missing.append(f"param {n}")
    if entry["kind"] in ("function", "method") and not (entry["returns"] or note.get("r")):
        missing.append("returns")
    return ("complete" if not missing else "partial"), missing
