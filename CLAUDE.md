# Stokastisk documentation site

Obey `.claude/skills/stokastisk-docs-maintain/SKILL.md` (modes: migrate-root, coverage, repair-publish, build, clean, seo, publish, audit); it overrides any older instruction, including the SDK sibling's former `stokastisk-docs-seo` guidance.

- Python: only `python3.13` / `python3.13 -m pip --user`. No venv, uv, Ruff, conda, poetry, pipx. Great Docs runs from source at the commit in `SOURCE.lock.json` via PYTHONPATH (Ruff omitted, fallback verified); Quarto 1.11.9 is standalone (`~/.local/opt/quarto-1.11.9`). No torch, vLLM, CUDA or models for docs.
- Build: `scripts/build_site.sh --validate [../Project-Stokastisk]` (SDK staged in a temp dir, static analysis only, `_site/` output, gitignored). CI: `.github/workflows/pages.yml`.
- Canonical URL: `https://stokastisk-ai.github.io/` (repository `stokastisk-ai/stokastisk-ai.github.io`, renamed from `stokastisk-docs` on 2026-11-20; old `/stokastisk-docs/...` paths are served as redirect pages). The SDK repo's own project site (`/stokastisk/simple/` package index, `/stokastisk/docs/`) shares the host and must never be touched or generated over.
- API docs: `website/api-notes*.yml` document SDK objects that lack docstrings (never edit the SDK); `scripts/api_coverage.py` must report 0 partial objects.
- Keep the repo lean (<6 MiB): never commit `_src/`, `_site/`, caches, envs or credentials. Never read `tokens.env`. SDK-side Claude files (`../Project-Stokastisk/CLAUDE.md`, its old skill) point here.
