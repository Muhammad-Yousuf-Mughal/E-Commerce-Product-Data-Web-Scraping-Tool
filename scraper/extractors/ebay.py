"""eBay product extractor (best-effort)."""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from .base import Product, ProductExtractor


class EbayExtractor(ProductExtractor):
    """Extracts product fields from an eBay item page."""

    site_name = "ebay"

    def can_handle(self, url: str) -> bool:
        return "ebay" in url.lower()

    def extract(self, html: str, url: str) -> Product:
        soup = BeautifulSoup(html, "lxml")
        product = Product(url=url, source_site="ebay")

        product.name = self._name(soup)
        product.price = self._price(soup)
        product.currency = self._currency(soup)
        product.rating = self._rating(soup)
        product.rating_count = self._rating_count(soup)
        product.availability, product.available = self._availability(soup)
        product.category = self._category(soup)
        product.description = self._description(soup)

        return product

    # ------------------------------------------------------------------ #
    def _name(self, soup: BeautifulSoup) -> str:
        element = soup.select_one("h1.ux-title-text") or soup.select_one(
            ".it-ttl"
        ) or soup.select_one("h1")
        if element:
            return element.get_text(strip=True)
        return ""

    def _price(self, soup: BeautifulSoup) -> Optional[float]:
        element = soup.select_one(".x-price-primary") or soup.select_one(
            ".x-price__value"
        ) or soup.select_one(".display-price")
        text = element.get_text(strip=True) if element else ""
        match = re.search(r"([\d,]+\.?\d*)", text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return None
        return None

    def _currency(self, soup: BeautifulSoup) -> Optional[str]:
        element = soup.select_one(".x-price-primary .x-price__currency") or soup.select_one(
            ".currency"
        )
        if element:
            return element.get_text(strip=True).upper()
        return None

    def _rating(self, soup: BeautifulSoup) -> Optional[float]:
        element = soup.select_one(".x-star-rating .x-star-rating__text") or soup.select_one(
            ".x-star-rating"
        )
        if element:
            text = element.get_text(strip=True) or element.get("aria-label", "")
            match = re.search(r"([\d.]+)", text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None
        return None

    def _rating_count(self, soup: BeautifulSoup) -> Optional[int]:
        element = soup.select_one(".x-star-rating .x-star-rating__count") or soup.select_one(
            "span[itemprop='reviewCount']"
        )
        if element:
            match = re.search(r"([\d,]+)", element.get_text())
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    return None
        return None

    def _availability(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[bool]]:
        element = soup.select_one(".x-store-availability") or soup.select_one(
            ".d-quantity__availability"
        )
        if not element:
            return None, None
        text = element.get_text(" ", strip=True).lower()
        available = None
        if "in stock" in text or "available" in text:
            available = True
        elif "out of stock" in text or "unavailable" in text:
            available = False
        return text, available

    def _category(self, soup: BeautifulSoup) -> Optional[str]:
        nav = soup.select_one(".breadcrumb")
        if not nav:
            return None
        links = nav.select("a")
        if links:
            last = links[-1].get_text(strip=True)
            return last or None
        return None

    def _description(self, soup: BeautifulSoup) -> Optional[str]:
        element = soup.select_one(".x-item-description") or soup.select_one(
            ".item-description"
        )
        if element:
            text = element.get_text(" ", strip=True)
            return text or None
        return None
