"""Registry that maps a URL to the most appropriate product extractor."""

from __future__ import annotations

from typing import List

from .amazon import AmazonExtractor
from .base import ProductExtractor
from .books_to_scrape import BooksToScrapeExtractor
from .ebay import EbayExtractor
from .generic import GenericExtractor

#: Order matters — first match wins.
_EXTRACTORS: List[ProductExtractor] = [
    AmazonExtractor(),
    EbayExtractor(),
    BooksToScrapeExtractor(),
    GenericExtractor(),
]

_KNOWN_DOMAINS = {
    "books.toscrape.com": "Books to Scrape (sandbox)",
    "scrapingclub.com": "Scraping Club (sandbox)",
    "quotes.toscrape.com": "Quotes to Scrape (sandbox)",
    "webscraper.io": "Web Scraper IO (sandbox)",
}


def get_extractor_for_url(url: str) -> ProductExtractor:
    """Return the first extractor that can handle ``url``.

    Falls back to the :class:`GenericExtractor` when no site-specific
    extractor matches.
    """
    for extractor in _EXTRACTORS:
        if extractor.can_handle(url):
            return extractor
    return GenericExtractor()


def get_all_extractors() -> List[ProductExtractor]:
    """Return the list of registered extractors."""
    return list(_EXTRACTORS)


def known_domain(url: str) -> str:
    """Return a friendly name for a domain if it is a known sandbox."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.lower()
    return _KNOWN_DOMAINS.get(domain, domain)
