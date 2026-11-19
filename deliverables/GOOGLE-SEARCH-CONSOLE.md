# Google Search Console instructions

Do these after the site is live at `https://stokastisk-ai.github.io/`. This is the same host as before but a new URL prefix (the site moved from `/stokastisk-docs/` to the host root), so add a **new** URL-prefix property for the root; Google's Change-of-Address tool applies only to domain moves and is not needed. The SDK repository's project site (`/stokastisk/...`) lives under the same host and is covered by the same root property. They need your Google login and cannot be done by an agent. Nothing here guarantees that Google will index or rank any page; indexing is Google's decision and can take days or weeks.

## 1. Add the property

1. Open <https://search.google.com/search-console> and choose **Add property**.
2. Choose **URL prefix** and enter `https://stokastisk-ai.github.io/` exactly (with the trailing slash and `https`). A *Domain* property is not possible: `github.io` is not a domain you control.
3. Verification method **HTML tag** is the easiest for this site. Google shows a line like `<meta name="google-site-verification" content="…">`. **Copy the value Google gives you; never invent or reuse a token.**

## 2. Keep the verification across builds

Add the tag to the Great Docs configuration so every rebuild contains it (`website/great-docs.yml`):

```yaml
include_in_header:
  - '<meta name="google-site-verification" content="PASTE-THE-VALUE-FROM-GOOGLE">'
```

Commit, push, let the `docs` workflow deploy, confirm with `curl -s https://stokastisk-ai.github.io/ | grep google-site-verification`, then press **Verify** in Search Console. Leave the tag in place permanently; removing it un-verifies the property.

(HTML-file verification also works: place the downloaded `google….html` file in `website/` and add it under `resources` per the Great Docs custom-pages guide, then confirm it is served at the site root. The meta tag avoids this.)

## 3. Submit the sitemap

In **Sitemaps**, enter `sitemap.xml` and submit. Expected: status *Success* and the number of discovered URLs close to the count in `reports/site-check.json` (`sitemap_urls`). Great Docs also lists the sitemap in the root `robots.txt` (now authoritative for the host; it allows everything).

## 4. Inspect and request indexing for key pages

In **URL Inspection**, test these URLs one at a time, check the *Canonical* field matches the page itself, then press **Request indexing** (a manual quota applies; do a handful, not all pages):

1. `https://stokastisk-ai.github.io/`
2. `https://stokastisk-ai.github.io/user-guide/installation.html`
3. `https://stokastisk-ai.github.io/user-guide/quickstart.html`
4. `https://stokastisk-ai.github.io/user-guide/release-verification.html`
5. `https://stokastisk-ai.github.io/reference/index.html`

Do **not** use the Indexing API: Google supports it only for job-posting and livestream pages. The sitemap plus a few manual requests is the supported route for documentation.

## 5. Review

* **Pages** report: expect *Indexed* to grow; investigate *Crawled, currently not indexed* and *Duplicate, Google chose different canonical* (the latter would indicate two live copies of the same page, for example if the old `/stokastisk/docs/` pages were not pointed at the new canonical URLs).
* **Enhancements / structured data**: the pages carry `SoftwareSourceCode` JSON-LD; there is no rich-result eligibility to expect.
* Exact-brand checks (`"Stokastisk" python sdk`, `site:stokastisk-ai.github.io`) are only supplementary evidence. Do not scrape Google in bulk.

## 6. What the property cannot cover

Search Console cannot verify `github.com` or `huggingface.co` pages. For those, improve titles, About text and links as in `GITHUB-HF-METADATA.md`; Google decides their indexing independently.

## 7. Legitimate ways to help discovery

Link to the site from places you control: the GitHub repository About/website field, the README, the Hugging Face model card, your portfolio and the Kaggle notebooks' descriptions. Do not buy links, trade links, post comment spam or stuff keywords.

## 8. Legacy URLs
Old `/stokastisk-docs/...` pages are redirect pages with a canonical on the matching root page. In Search Console, if the old property still exists, expect them to drop out as Google recrawls; do not submit them. Check **Pages > Page with redirect** later. Nothing here guarantees indexing or ranking.
