# Stokastisk documentation: status (2026-11-20, migrate-root + coverage)

SDK revision `387c414295fbd65e6c93099c58dfeee43c3ce3fc` (v0.1.0, wheel build 5; unchanged). Great Docs source `d9f2603f0b1fbaa64b56de2b370c1d6d7a08de6e` (no Ruff), Quarto 1.11.9 standalone, Python 3.13.15. Canonical site `https://stokastisk-ai.github.io/`; repo `stokastisk-ai/stokastisk-ai.github.io` (renamed from `stokastisk-docs`, id 1462384714; rollback commit `cb77c33`).

## API coverage (recomputed from source; `scripts/api_coverage.py`)
| Measure | 2026-11-19 baseline | Now |
|---|---|---|
| public module-level names | 203 | 203 |
| own Great Docs page / module-index only / omitted data tables / internal helpers | 137 / 26 / 36 / 4 | 137 / 26 / 36 / 4 |
| `__all__` names documented | 49 of 51 | 50 of 51 (`SamplingParams` is upstream vLLM, explained in the API map) |
| class methods with Great Docs page / index only | 18 / 29 | 18 / 29 (all 47 now also have a detail section) |
| objects with a detail section (signature, typed parameter table with meanings, returns, raises, source link, status) | 0 | **275 of 275** |
| fully documented / internal helper (justified) / partial | n/a | **252 / 23 / 0** |
| h1 duplicates / dangling anchors | 169 pages / 356 links | 0 / 0 (post-processing) |

"Fully documented" requires a summary (source docstring or site note) and a meaning for every parameter; the origin of each text is stated on its section. Notes live in `website/api-notes*.yml`; the SDK is untouched. Source docstring gaps remain in the SDK (13 lint errors); one source finding recorded: `telemetry.nvml` docstring says NVML first, the code samples through nvidia-smi.

## Validation (final local build, exit 0)
Great Docs SEO audit pass; `check_site.py`: 0 failures (192 pages, 191 unique titles and descriptions, 191 sitemap URLs, 0 broken links or anchors, one h1 per page, 192 legacy redirect pages verified, no private maintenance text in skills/llms files, install hash = RELEASE.json build 5); `check-links`: 9 external URLs OK (source links are checked locally against the SDK tree instead of over HTTP); 31 Python examples parse. `check-examples` not run (needs vLLM/GPU). SDK tests not rerun.

## Evidence labels
Build 3 ran on Kaggle (withdrawn). Build 5 is CPU-verified and inherits that evidence through audited equivalence. No benchmark numbers are published.
