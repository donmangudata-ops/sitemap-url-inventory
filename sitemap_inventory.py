"""sitemap-url-inventory: list every URL in a site's sitemaps, and diff two lists.

Standard library only. Usage:
    python sitemap_inventory.py extract https://example.com -o urls.csv
    python sitemap_inventory.py extract https://example.com --contains /blog/
    python sitemap_inventory.py diff old.csv new.csv
"""
import argparse
import csv
import gzip
import sys
import time
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
FIELDS = ["url", "lastmod", "changefreq", "priority", "sitemap"]
DEFAULT_UA = "sitemap-url-inventory/1.0 (+https://github.com/donmangudata-ops/sitemap-url-inventory)"


class Fetcher:
    def __init__(self, user_agent=DEFAULT_UA, delay=0.5, timeout=30):
        self.headers = {"User-Agent": user_agent}
        self.delay = delay
        self.timeout = timeout

    def get(self, url):
        time.sleep(self.delay)
        with urlopen(Request(url, headers=self.headers), timeout=self.timeout) as r:
            data = r.read()
        if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        return data


def find_sitemaps(site, fetch):
    """Sitemaps declared in robots.txt, else the usual default locations."""
    base = site.rstrip("/")
    try:
        text = fetch.get(base + "/robots.txt").decode("utf-8", "replace")
        declared = [l.split(":", 1)[1].strip() for l in text.splitlines()
                    if l.lower().startswith("sitemap:")]
        if declared:
            return declared
    except (HTTPError, URLError):
        pass
    return [base + "/sitemap.xml", base + "/sitemap_index.xml"]


def _text(el, name):
    child = el.find(NS + name)
    return child.text.strip() if child is not None and child.text else ""


def read_sitemap(url, fetch, seen, errors):
    """Yield rows from one sitemap; follow sitemap indexes recursively."""
    if url in seen:
        return
    seen.add(url)
    try:
        data = fetch.get(url)
    except (HTTPError, URLError, OSError) as e:
        errors.append((url, str(e)))
        return
    if not data.lstrip().startswith(b"<"):  # plain-text sitemap
        for line in data.decode("utf-8", "replace").splitlines():
            if line.strip().startswith("http"):
                yield {"url": line.strip(), "lastmod": "", "changefreq": "", "priority": "", "sitemap": url}
        return
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        errors.append((url, "not XML: " + str(e)))
        return
    if root.tag == NS + "sitemapindex":
        for sm in root.iter(NS + "sitemap"):
            loc = _text(sm, "loc")
            if loc:
                yield from read_sitemap(loc, fetch, seen, errors)
        return
    for u in root.iter(NS + "url"):
        loc = _text(u, "loc")
        if loc:
            yield {"url": loc, "lastmod": _text(u, "lastmod"), "changefreq": _text(u, "changefreq"),
                   "priority": _text(u, "priority"), "sitemap": url}


def extract(site, fetch, contains=None):
    seen, errors, rows, urls = set(), [], [], set()
    for sm in find_sitemaps(site, fetch):
        for row in read_sitemap(sm, fetch, seen, errors):
            if contains and contains not in row["url"]:
                continue
            if row["url"] not in urls:
                urls.add(row["url"])
                rows.append(row)
    return rows, errors


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["url"]: r for r in csv.DictReader(f)}


def diff(old_path, new_path):
    old, new = load_csv(old_path), load_csv(new_path)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(u for u in set(old) & set(new) if old[u].get("lastmod") != new[u].get("lastmod"))
    return added, removed, changed


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="list all URLs from a site's sitemaps")
    e.add_argument("site")
    e.add_argument("-o", "--out", help="CSV file (default: print to stdout)")
    e.add_argument("--contains", help="keep only URLs that contain this text")
    e.add_argument("--user-agent", default=DEFAULT_UA)
    e.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    d = sub.add_parser("diff", help="compare two CSV files from extract")
    d.add_argument("old")
    d.add_argument("new")
    a = p.parse_args(argv)

    if a.cmd == "extract":
        rows, errors = extract(a.site, Fetcher(a.user_agent, a.delay), a.contains)
        out = open(a.out, "w", newline="", encoding="utf-8") if a.out else sys.stdout
        w = csv.DictWriter(out, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
        if a.out:
            out.close()
        print(f"{len(rows)} URLs", file=sys.stderr)
        for url, err in errors:
            print(f"error: {url}: {err}", file=sys.stderr)
        return 0 if rows else 1

    added, removed, changed = diff(a.old, a.new)
    for label, items in (("added", added), ("removed", removed), ("lastmod changed", changed)):
        print(f"{label}: {len(items)}")
        for u in items:
            print("  " + u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
