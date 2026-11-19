# Deployment

Canonical site: `https://stokastisk-ai.github.io/` (organisation GitHub Pages site, Actions source) from `stokastisk-ai/stokastisk-ai.github.io`, branch `main`. History: the repository was `stokastisk-docs` (site at `/stokastisk-docs/`) until the 2026-11-20 rename; rollback commit before the migration: `cb77c33`.

The workflow `.github/workflows/pages.yml` builds from the immutable SDK commit in `SOURCE.lock.json`, validates, and deploys only from `stokastisk-ai/stokastisk-ai.github.io`. It never touches the SDK repository, its `gh-pages` branch, `/stokastisk/simple/` or `/stokastisk/docs/` (the SDK's project site shares the host; the build refuses to emit a `/stokastisk/` directory).

## Old URLs
GitHub Pages cannot send HTTP 301. After the rename the old project path `/stokastisk-docs/...` is served by this site from generated redirect pages (`stokastisk-docs/<page>.html`): `rel=canonical` to the matching root page, an immediate meta refresh and a visible link, one per page; they are not in the sitemap. Non-HTML old files (`/stokastisk-docs/sitemap.xml`, `robots.txt`, `llms.txt`) are not redirected. The old SDK guide `/stokastisk/docs/` stays; `patches/sdk-repo-docs-links.patch` (not applied; needs the SDK owner) makes its pages declare canonicals on the new site.

## Update
Change `sdk.commit` in `SOURCE.lock.json`, run `scripts/build_site.sh --validate`, commit, push. Verify live: `/`, `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/og-image.png`, `/user-guide/installation.html`, `/reference/index.html`, an old `/stokastisk-docs/user-guide/installation.html`, and `https://stokastisk-ai.github.io/stokastisk/simple/` (must stay 200).

## Rollback
`gh repo rename stokastisk-docs --repo stokastisk-ai/stokastisk-ai.github.io --yes`, set `site_url` back and redeploy (or revert to `cb77c33`). The SDK site is unaffected either way.
