# Stokastisk documentation site

Obey `.claude/skills/stokastisk-docs-maintain/SKILL.md` (default mode `repair-publish`); it overrides any older instructions, including the SDK sibling's `stokastisk-docs-seo` skill (it assumed venvs and a root URL).

- Python: only `python3.13` / `python3.13 -m pip --user`. No venv, uv, Ruff, conda, poetry, pipx. Great Docs runs from source at the commit in `SOURCE.lock.json` via PYTHONPATH (Ruff omitted, fallback verified); Quarto 1.11.9 is standalone (`~/.local/opt/quarto-1.11.9`).
- Build: `scripts/build_site.sh --validate [../Project-Stokastisk]` (stages the pinned SDK in a temp dir, static analysis only, writes `_site/`). CI: `.github/workflows/pages.yml`.
- Canonical URL: `https://stokastisk-ai.github.io/stokastisk-docs/` (repo name stays `stokastisk-docs`). Never touch the SDK repo, its `gh-pages` or `/stokastisk/simple/`.
- Keep the repo lean (<6 MiB): never commit `_src/`, `_site/`, caches, envs or credentials. Never read `tokens.env`.
