import unittest

from telescope.collectors import rss

RSS2 = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>US &amp; China talks</title><link>https://a.com/1</link>
<description>&lt;p&gt;Leaders met.&lt;/p&gt;</description>
<pubDate>Mon, 31 Aug 2026 10:00:00 GMT</pubDate></item>
<item><title>Russia missile strike</title><link>https://a.com/2</link>
<description>Attack reported.</description></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>A</title>
<entry><title>Atom item</title>
<link href="https://b.com/1"/>
<summary>Sum.</summary><updated>2026-08-31T10:00:00Z</updated></entry></feed>"""

RDF = b"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>C</title></channel>
<item><title>RDF item</title><link>https://c.com/1</link>
<description>D.</description><dc:date>2026-08-31T10:00:00Z</dc:date></item>
</rdf:RDF>"""


class TestRss(unittest.TestCase):
    def test_rss2(self):
        items = rss.parse_feed(RSS2)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"], "US & China talks")
        self.assertEqual(items[1]["link"], "https://a.com/2")

    def test_atom(self):
        items = rss.parse_feed(ATOM)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["link"], "https://b.com/1")
        self.assertEqual(items[0]["date"], "2026-08-31T10:00:00Z")

    def test_rdf(self):
        items = rss.parse_feed(RDF)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "RDF item")

    def test_helpers(self):
        self.assertEqual(rss.strip_html("<p>a &amp; b</p>"), "a & b")
        self.assertTrue(rss.parse_date("Mon, 31 Aug 2026 10:00:00 GMT")
                        .startswith("2026-08-31"))


if __name__ == "__main__":
    unittest.main()
