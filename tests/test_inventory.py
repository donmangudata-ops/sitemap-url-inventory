import csv
import gzip
import http.server
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sitemap_inventory as si  # noqa: E402

URLSET = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          '<url><loc>{b}/a</loc><lastmod>2026-01-01</lastmod></url>'
          '<url><loc>{b}/blog/b</loc><lastmod>2026-02-01</lastmod><priority>0.8</priority></url></urlset>')


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=cls.dir, **k))
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        b = cls.base
        w = lambda n, d: open(os.path.join(cls.dir, n), "wb").write(d if isinstance(d, bytes) else d.encode())
        w("robots.txt", f"User-agent: *\nSitemap: {b}/index.xml\n")
        w("index.xml", f'<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<sitemap><loc>{b}/posts.xml.gz</loc></sitemap><sitemap><loc>{b}/pages.txt</loc></sitemap>'
                       f'<sitemap><loc>{b}/missing.xml</loc></sitemap><sitemap><loc>{b}/index.xml</loc></sitemap></sitemapindex>')
        w("posts.xml.gz", gzip.compress(URLSET.format(b=b).encode()))
        w("pages.txt", f"{b}/c\n{b}/a\n")
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_extract_follows_index_gzip_txt_and_dedupes(self):
        rows, errors = si.extract(self.base, si.Fetcher(delay=0))
        self.assertEqual(sorted(r["url"] for r in rows), [self.base + "/a", self.base + "/blog/b", self.base + "/c"])
        self.assertEqual(next(r for r in rows if r["url"].endswith("/blog/b"))["priority"], "0.8")
        self.assertEqual(len(errors), 1)  # missing.xml reported, run continues; self-loop ignored

    def test_contains_filter(self):
        rows, _ = si.extract(self.base, si.Fetcher(delay=0), contains="/blog/")
        self.assertEqual([r["url"] for r in rows], [self.base + "/blog/b"])

    def test_diff(self):
        d = tempfile.mkdtemp()
        def save(name, rows):
            with open(os.path.join(d, name), "w", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=si.FIELDS); wr.writeheader(); wr.writerows(rows)
        r = lambda u, m: {"url": u, "lastmod": m, "changefreq": "", "priority": "", "sitemap": ""}
        save("old.csv", [r("x", "1"), r("y", "1")])
        save("new.csv", [r("y", "2"), r("z", "1")])
        self.assertEqual(si.diff(os.path.join(d, "old.csv"), os.path.join(d, "new.csv")), (["z"], ["x"], ["y"]))


if __name__ == "__main__":
    unittest.main()
