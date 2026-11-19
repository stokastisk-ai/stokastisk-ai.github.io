# Proposed GitHub and Hugging Face metadata (not applied)

## GitHub repository `stokastisk-ai/stokastisk`

Current (read-only API, 2026-11-19): description "Python 3.13 SDK with bundled vLLM 0.25.1 for Kaggle's 2x Tesla T4 (SM75, CUDA 13.0) — Triton attention, FP16; Kaggle-tested models listed in the docs"; homepage `https://huggingface.co/waqasm86/stokastisk`; topics `cuda-13, kaggle, python313, tesla-t4, triton, vllm`.

Proposed (after the new site is live and verified):

```bash
# website field: the single canonical documentation URL
gh repo edit stokastisk-ai/stokastisk --homepage "https://stokastisk-ai.github.io/"
# About text: plain, factual, includes the exact brand and the supported hardware (<=350 chars)
gh repo edit stokastisk-ai/stokastisk --description "Independent open-source Python 3.13 SDK: bundled vLLM 0.25.1 with Triton attention (SM75, CUDA 13.0) for Kaggle's dual Tesla T4 GPUs. TP, PP and replicas, structured output, OpenAI-compatible server."
# topics: add accurate ones only
gh repo edit stokastisk-ai/stokastisk --add-topic llm-inference --add-topic nvidia-t4 --add-topic tensor-parallelism --add-topic openai-compatible --add-topic python-sdk
```

These change a public repository's settings: run them only with your approval. The GitHub Pages setting of that repository must stay as it is (`gh-pages` branch, root).

## README

`patches/sdk-repo-docs-links.patch` adds a "Documentation" section with the new URL. It keeps the existing install commands and evidence tables.

## `[project.urls]` in `pyproject.toml` (not proposed for now)

Adding `Documentation`/`Source` URLs would change wheel `METADATA` and therefore require a new wheel build, which the version policy and the frozen-bytes rule forbid for a documentation task. Revisit only with the next deliberate wheel build.

## Hugging Face model card `waqasm86/stokastisk`

Keep the YAML front matter and the current wheel URL. The patch changes only the link sentence in `docs/HUB_README.md` (the card's source) to "Documentation and API reference: https://stokastisk-ai.github.io/". Uploading the card to Hugging Face is a separate approval step; do not upload the wheel again.

Optional front-matter additions (valid model-card fields): none required. Existing tags (`vllm, kaggle, tesla-t4, sm75, cuda-13, triton, inference, python-3.13`) already describe the project.

## Brand disambiguation

The site states that Stokastisk is independent and not affiliated with vLLM, NVIDIA, Kaggle or any company named Stochastic. Keep the same sentence in the README and card if you want search engines and readers to see one consistent description.
