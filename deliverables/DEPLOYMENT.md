# Deployment

Canonical site: `https://stokastisk-ai.github.io/stokastisk-docs/` (GitHub Pages, Actions source) from `stokastisk-ai/stokastisk-docs`, branch `main`. The workflow `.github/workflows/pages.yml` builds from the immutable SDK commit in `SOURCE.lock.json`, validates, and deploys only from that repository. It never touches the SDK repository, its `gh-pages` branch or `/stokastisk/simple/`.

Update: change `sdk.commit` in `SOURCE.lock.json`, run `scripts/build_site.sh --validate`, commit, push.

Verify live: `curl -s -o /dev/null -w '%{http_code}\n'` on `/`, `/sitemap.xml`, `/robots.txt`, `/llms.txt`, `/og-image.png`, `/user-guide/installation.html`, `/reference/index.html` under the canonical URL, and on `https://stokastisk-ai.github.io/stokastisk/simple/` (must stay 200).

Note: `robots.txt` of a project site is served at `/stokastisk-docs/robots.txt`; crawlers only honour the host-root `/robots.txt`, which belongs to the organisation, not this repo. Use the scoped sitemap in Search Console.

Optional SDK patch: `patches/sdk-repo-docs-links.patch` (needs the SDK owner's decision; not applied).
