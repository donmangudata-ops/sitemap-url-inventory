# sitemap-url-inventory

List every URL in a website's sitemaps as a CSV, and compare two lists to see what was added, removed or updated. One Python file, standard library only.

Use it for:

- **Site migrations.** Export the old site, export the new site, run `diff`. You get the pages that disappeared.
- **SEO checks.** See every URL the site tells search engines about, with `lastmod`, `changefreq` and `priority`.
- **Input for other tools.** A clean URL list for a crawler, a screenshot job or a page-to-Markdown job.

## Why sitemap tools return nothing

Most "0 URLs" results have one of these causes. This script handles all four:

| Cause | What the script does |
|---|---|
| The sitemap is not at `/sitemap.xml` | Reads the `Sitemap:` lines in `robots.txt` first |
| The file is a sitemap index | Follows every child sitemap, and skips loops |
| The sitemap is gzipped (`.xml.gz`) | Unpacks it |
| The sitemap is plain text | Reads one URL per line |

A broken child sitemap does not stop the run. It is reported at the end.

## Install

```bash
git clone https://github.com/donmangudata-ops/sitemap-url-inventory
cd sitemap-url-inventory
python sitemap_inventory.py --help
```

Python 3.8 or later. No packages to install.

## Usage

```bash
# all URLs to a CSV
python sitemap_inventory.py extract https://example.com -o urls.csv

# only URLs that contain /blog/
python sitemap_inventory.py extract https://example.com --contains /blog/ -o blog.csv

# what changed between two exports
python sitemap_inventory.py diff old.csv new.csv
```

CSV columns: `url, lastmod, changefreq, priority, sitemap` (the sitemap file the URL came from). Duplicate URLs are removed.

Example `diff` output:

```
added: 1
  https://example.com/new-page
removed: 1
  https://example.com/old-page
lastmod changed: 1
  https://example.com/pricing
```

## Be polite

The script waits 0.5 seconds between requests (`--delay`). Set `--user-agent` to something that identifies you. If a site blocks automated access, respect that.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests start a local web server with a sitemap index, a gzipped sitemap, a text sitemap, a missing file and a loop.

## Hosted version (optional)

If you don't want to run this yourself, I also sell a hosted version on Apify: [Sitemap Extractor](https://apify.com/conserving_celerytop/sitemap-url-extractor?utm_source=github&utm_medium=readme&utm_campaign=sitemap-url-inventory). It runs on a schedule in the cloud, exports to CSV, JSON or Excel, and connects to Make, n8n and Zapier. It charges $0.50 per 1,000 URLs, and sites without a sitemap are free.

Disclosure: I built that Actor, and it is paid. This repository is free and works without it. The code was written with help from an AI assistant and is covered by the tests above.

## License

MIT
