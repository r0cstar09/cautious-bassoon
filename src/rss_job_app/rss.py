import feedparser
from typing import Iterable, Dict

def fetch_feed(url: str) -> Iterable[Dict]:
    """Yield raw feed entries from an RSS/Atom feed URL."""
    d = feedparser.parse(url)
    for entry in d.entries:
        yield entry
