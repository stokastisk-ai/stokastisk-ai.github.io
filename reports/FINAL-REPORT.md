# Stokastisk documentation: final report (2026-11-19)

Local build only. Nothing was pushed, renamed, uploaded or configured remotely.

## Source and tools
SDK commit `387c414295fbd65e6c93099c58dfeee43c3ce3fc` (v0.1.0 project, wheel build 5, unchanged). Great Docs `0.17.1.dev1741+gd9f2603f0` (commit `d9f2603f0b1fbaa64b56de2b370c1d6d7a08de6e`), Quarto 1.11.9 (PyPI `quarto-cli`), Python 3.13.15, harper-cli 3.3.0 (isolated in `.tools/`).

## Architecture
SDK repo = source of truth. This repo = `website/` (config, 19 hand-written guide pages + homepage), generated pages (feature matrix, module index from the SDK), `scripts/`, `SOURCE.lock.json`, `.github/workflows/pages.yml`. Static analysis only; vLLM/torch/CUDA never installed in the docs venv.

## Results (final run, SDK staged by cloning the pinned commit from GitHub, as CI does)
| Step | Result |
|---|---|
| `great-docs build` | exit 0, 180 HTML pages, 179 sitemap URLs, 0 warnings, 4m34s |
| `great-docs seo` | all checks passed (canonicals, descriptions, JSON-LD, alt text, sitemap, robots) |
| `scripts/check_site.py` | 0 failures: unique titles 179, unique descriptions 179, 0 broken internal links, OG image present, install command = RELEASE.json build 5 and SHA256, no secrets or local paths. 3 warnings (upstream, see below) |
| `scripts/api_coverage.py` | 0 gaps. 203 public names: 137 with a page, 26 listed in the module index only (no docstring), 40 omitted with reason (data tables, internal helpers). 49 of 51 `__all__` names documented; `SamplingParams` (upstream vLLM) and `__version__` omitted deliberately |
| `great-docs check-links --docs-only` | 9 OK, 0 broken |
| `great-docs lint` | exit 1: 13 errors, 4 warnings, all `missing-docstring` in the SDK source (e.g. `StokastiskConfig`, `Topology`, `LIMITS`); plus ambiguous-autolink warnings. Not fixed: changing `sdk/` would alter the frozen wheel source |
| `great-docs proofread` | grammar-only on hand-written pages: style/hyphenation hits and code identifiers, no prose errors needing change |
| `great-docs check-examples` | not run: it executes code and needs vLLM/GPU |
| SDK CPU tests (isolated venv) | 242 passed, 13 skipped (pinned vLLM wheel absent), 1 failed (`test_hardening::test_import_does_not_start_cuda`: torch not installed), `test_engine_lifecycle.py` not collected (needs torch). Docs/version/release tests passed, including with the proposed patch (43 passed) |

Upstream Great Docs findings (warnings only): social-card image not copied to `_site` (fixed in `postprocess_site.py`); API pages have two `<h1>`; autolinks emit `#stokastisk.X` fragments that don't exist.

## Not claimed
Kaggle-tested = build 3 (withdrawn). Build 5 = CPU-verified, evidence inherited; no GPU run here. No benchmarks published. Google indexing/ranking not guaranteed.

## Remaining limitations
Rename of `stokastisk-docs` to `stokastisk-ai.github.io` needed for the configured canonical URL; SDK docstring gaps; old `/stokastisk/docs/` remains until the optional patch is applied; Search Console verification needs your login; link check covers only 9 URLs.

## Deploy
See `deliverables/DEPLOYMENT.md` (exact commands), `GOOGLE-SEARCH-CONSOLE.md`, `GITHUB-HF-METADATA.md`, `patches/sdk-repo-docs-links.patch`.

## Update 2026-11-19 (maintain skill, repair-publish)
Canonical URL is now `https://stokastisk-ai.github.io/stokastisk-docs/`. No venv, no Ruff: Great Docs runs from source at the pinned commit via PYTHONPATH (Ruff only gates formatting via `shutil.which("ruff")`), Quarto 1.11.9 is standalone. Rebuilt and validated: 179 sitemap URLs, Great Docs SEO pass, 0 check_site failures, 0 broken links. Earlier SDK test results above are unchanged (not rerun).
