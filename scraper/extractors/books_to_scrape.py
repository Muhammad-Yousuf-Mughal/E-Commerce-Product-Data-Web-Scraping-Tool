"""Books to Scrape (books.toscrape.com) extractor.

This is a scraping sandbox purpose-built for practice, so it is the most
reliable site for end-to-end verification of the pipeline.
"""

from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup

from .base import Product, ProductExtractor

_RATING_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


class BooksToScrapeExtractor(ProductExtractor):
    """Extracts product fields from a Books to Scrape detail page."""

    site_name = "books_to_scrape"

    def can_handle(self, url: str) -> bool:
        return "books.toscrape.com" in url.lower()

    def extract(self, html: str, url: str) -> Product:
        soup = BeautifulSoup(html, "lxml")
        product = Product(url=url, source_site="books.toscrape.com")

        product.name = self._name(soup)
        product.price = self._price(soup)
        product.rating = self._rating(soup)
        product.availability, product.available = self._availability(soup)
        product.category = self._category(soup)
        product.description = self._description(soup)
        product.currency = "GBP"

        return product

    # ------------------------------------------------------------------ #
    def _name(self, soup: BeautifulSoup) -> str:
        element = soup.select_one(".product_main h1")
        if element:
            return element.get_text(strip=True)
        return ""

    def _price(self, soup: BeautifulSoup) -> Optional[float]:
        element = soup.select_one(".price_color")
        if not element:
            return None
        text = element.get_text(strip=True).replace("£", "").replace(",", "")
        try:
            return float(text)
        except ValueError:
            return None

    def _rating(self, soup: BeautifulSoup) -> Optional[float]:
        element = soup.select_one("p.star-rating")
        if not element:
            return None
        classes = [cls.lower() for cls in (element.get("class") or [])]
        for name, value in _RATING_MAP.items():
            if name in classes:
                return float(value)
        return None

    def _availability(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[bool]]:
        element = soup.select_one(".availability")
        if not element:
            return None, None
        text = element.get_text(" ", strip=True)
        available = "in stock" in text.lower()
        return text, available

    def _category(self, soup: BeautifulSoup) -> Optional[str]:
        breadcrumb = soup.select_one("ul.breadcrumb")
        if not breadcrumb:
            return None
        links = breadcrumb.select("li a")
        if len(links) >= 2:
            return links[1].get_text(strip=True)
        return None

    def _description(self, soup: BeautifulSoup) -> Optional[str]:
        element = soup.select_one("#product_description")
        if not element:
            return None
        parent = element.find_parent()
        if parent:
            content = parent.select_one("p")
            if content:
                text = content.get_text(" ", strip=True)
                return text or None
        return None
