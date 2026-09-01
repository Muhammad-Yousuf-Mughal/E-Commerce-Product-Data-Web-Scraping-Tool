"""Product extractor package."""

from .amazon import AmazonExtractor
from .base import Product, ProductExtractor
from .books_to_scrape import BooksToScrapeExtractor
from .ebay import EbayExtractor
from .generic import GenericExtractor
from .registry import get_all_extractors, get_extractor_for_url, known_domain

__all__ = [
    "Product",
    "ProductExtractor",
    "AmazonExtractor",
    "EbayExtractor",
    "BooksToScrapeExtractor",
    "GenericExtractor",
    "get_extractor_for_url",
    "get_all_extractors",
    "known_domain",
]
