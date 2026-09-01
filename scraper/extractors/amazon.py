"""Amazon.com product extractor (best-effort).

Note: Amazon operates aggressive anti-bot measures. Plain ``requests`` may be
served a CAPTCHA/robot page. This adapter implements the standard selectors
so it works whenever the HTML is actually returned; for reliable use against
Amazon you would need a dynamic browser (Playwright/Selenium), which can be
enabled separately.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from .base import Product, ProductExtractor


class AmazonExtractor(ProductExtractor):
    """Extracts product fields from an Amazon product detail page."""

    site_name = "amazon"

    def can_handle(self, url: str) -> bool:
        return "amazon" in url.lower()

    def extract(self, html: str, url: str) -> Product:
        soup = BeautifulSoup(html, "lxml")
        product = Product(url=url, source_site="amazon")

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
        element = soup.select_one("#productTitle")
        if element:
            text = element.get_text(strip=True)
            if text:
                return text
        if soup.title:
            return soup.title.string.strip().split(":")[0].strip()
        return ""

    def _price(self, soup: BeautifulSoup) -> Optional[float]:
        element = soup.select_one("#corePrice_feature_div .a-offscreen") or soup.select_one(
            "#priceblock_ourprice, .a-price .a-offscreen"
        )
        text = element.get_text(strip=True) if element else ""
        match = re.search(r"([\d,]+\.?\d*)", text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return None
        return None

    def _currency(self, soup: BeautifulSoup) -> Optional[str]:
        element = soup.select_one(".a-price-symbol")
        if element:
            symbol = element.get_text(strip=True)
            mapping = {
                "$": "USD", "£": "GBP", "€": "EUR", "₹": "INR",
                "¥": "JPY", "₩": "KRW", "₽": "RUB", "R$": "BRL",
                "CA$": "CAD", "A$": "AUD", "CHF": "CHF", "₪": "ILS",
                "MX$": "MXN", "₺": "TRY", "PKR": "PKR", "kr": "SEK",
            }
            return mapping.get(symbol, symbol or None)
        return None

    def _rating(self, soup: BeautifulSoup) -> Optional[float]:
        element = soup.select_one("#acrPopover .a-icon-alt") or soup.select_one(
            "span.a-icon-alt"
        )
        if element:
            text = element.get_text(strip=True)
            match = re.search(r"([\d.]+)\s*out of 5", text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None
        return None

    def _rating_count(self, soup: BeautifulSoup) -> Optional[int]:
        element = soup.select_one("#acrCustomerReviewText")
        if element:
            match = re.search(r"([\d,]+)", element.get_text())
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    return None
        return None

    def _availability(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[bool]]:
        element = soup.select_one("#availability") or soup.select_one(
            "#availability .a-color-success"
        )
        if not element:
            return None, None
        text = element.get_text(strip=True).lower()
        available = None
        if "in stock" in text or "available" in text:
            available = True
        elif "out of stock" in text or "unavailable" in text:
            available = False
        return text, available

    def _category(self, soup: BeautifulSoup) -> Optional[str]:
        nav = soup.select_one("#wayfinding-breadcrumbs_feature_div")
        if not nav:
            return None
        links = nav.select("a")
        if links:
            return links[-1].get_text(strip=True)
        return None

    def _description(self, soup: BeautifulSoup) -> Optional[str]:
        element = soup.select_one("#productDescription") or soup.select_one(
            "#feature-bullets"
        )
        if element:
            text = element.get_text(" ", strip=True)
            return text or None
        return None
