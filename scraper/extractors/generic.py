"""Generic extractor using JSON-LD, microdata, meta tags and heuristics.

This is the primary real-world extraction path. Most e-commerce product
pages embed structured data (``application/ld+json``) or Open Graph meta
tags, which we parse into a :class:`Product`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .base import Product, ProductExtractor

PRICE_PATTERN = re.compile(r"([0-9][0-9,]*\.?[0-9]*)")


class GenericExtractor(ProductExtractor):
    """Best-effort extractor that works on a wide range of sites."""

    site_name = "generic"

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def extract(self, html: str, url: str) -> Product:
        soup = BeautifulSoup(html, "lxml")
        product = Product(url=url, source_site=self._site_from_url(url))

        data = self._first_json_ld(soup)
        if data:
            self._apply_json_ld(product, data)

        self._apply_meta(product, soup)
        self._apply_heuristics(product, soup)

        if not product.name:
            product.name = self._extract_title(soup)
        if not product.url:
            product.url = url

        return product

    def can_handle(self, url: str) -> bool:
        return True  # generic fallback handles everything

    # ------------------------------------------------------------------ #
    # JSON-LD
    # ------------------------------------------------------------------ #
    def _first_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = script.string or script.get_text()
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            candidate = self._find_product_node(data)
            if candidate:
                return candidate
        return None

    def _find_product_node(self, data: Any) -> Optional[Dict[str, Any]]:
        """Locate a node that looks like a product across lists/graphs."""
        if isinstance(data, list):
            for item in data:
                found = self._find_product_node(item)
                if found:
                    return found
            return None
        if not isinstance(data, dict):
            return None

        node_type = data.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        for t in types:
            if t and "Product" in str(t):
                return data

        if "@graph" in data:
            return self._find_product_node(data["@graph"])

        for value in data.values():
            found = self._find_product_node(value)
            if found:
                return found
        return None

    def _apply_json_ld(self, product: Product, data: Dict[str, Any]) -> None:
        name = data.get("name")
        if name and isinstance(name, str):
            product.name = name.strip()

        offers = data.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else None
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice")
            if price is None and "priceSpecification" in offers:
                spec = offers["priceSpecification"]
                if isinstance(spec, dict):
                    price = spec.get("price")
            product.price = self._to_float(price)
            currency = offers.get("priceCurrency")
            if currency:
                product.currency = str(currency).upper()
            availability = offers.get("availability")
            if availability:
                product.availability = str(availability)
                product.available = self._availability_bool(availability)

        aggregate = data.get("aggregateRating")
        if isinstance(aggregate, dict):
            rating = aggregate.get("ratingValue")
            product.rating = self._to_float(rating)
            count = aggregate.get("reviewCount") or aggregate.get("ratingCount")
            product.rating_count = self._to_int(count)

        image = data.get("image")
        if image and not product.url and isinstance(image, str):
            pass  # url handled elsewhere

        description = data.get("description")
        if description and isinstance(description, str):
            product.description = description.strip()

        category = data.get("category")
        if category and isinstance(category, str):
            product.category = category.strip()

    # ------------------------------------------------------------------ #
    # Meta / Open Graph
    # ------------------------------------------------------------------ #
    def _apply_meta(self, product: Product, soup: BeautifulSoup) -> None:
        meta_map = {
            "og:title": "name",
            "og:price:amount": "price",
            "product:price:amount": "price",
            "og:description": "description",
            "product:price:currency": "currency",
            "product:availability": "availability",
            "og:url": "url",
        }
        for prop, attr in meta_map.items():
            if getattr(product, attr):
                continue
            tag = soup.find("meta", attrs={"property": prop}) or soup.find(
                "meta", attrs={"name": prop}
            )
            if tag and tag.get("content"):
                value = tag["content"].strip()
                if attr == "price":
                    product.price = self._to_float(value)
                elif attr == "currency":
                    product.currency = value.upper()
                else:
                    setattr(product, attr, value)

    # ------------------------------------------------------------------ #
    # Heuristics
    # ------------------------------------------------------------------ #
    def _apply_heuristics(self, product: Product, soup: BeautifulSoup) -> None:
        if product.rating is None:
            product.rating = self._find_rating(soup)
        if product.price is None:
            product.price = self._find_price(soup)

    def _find_rating(self, soup: BeautifulSoup) -> Optional[float]:
        for element in soup.find_all(attrs={"itemprop": "ratingValue"}):
            value = self._to_float(element.get_text())
            if value is not None:
                return value
        for element in soup.select("[data-rating], [class*='rating']"):
            text = element.get_text()
            match = re.search(r"([0-5]\.?[0-9]*)\s*(?:/|out of|stars?)", text)
            if match:
                return self._to_float(match.group(1))
        return None

    def _find_price(self, soup: BeautifulSoup) -> Optional[float]:
        selectors = [
            "[itemprop='price']",
            "[class*='price'] [class*='amount']",
            ".price",
            ".product-price",
            "[data-price]",
        ]
        for selector in selectors:
            for element in soup.select(selector):
                text = element.get("content") or element.get_text()
                value = self._parse_price(text)
                if value is not None:
                    return value
        # Try Open Graph price again as fallback
        return None

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _site_from_url(url: str) -> str:
        return urlparse(url).netloc.lower()

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(",", "").replace("$", "").strip()
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        match = re.search(r"\d+", str(value))
        return int(match.group(0)) if match else None

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        if not text:
            return None
        match = PRICE_PATTERN.search(text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return None
        return None

    @staticmethod
    def _availability_bool(value: str) -> Optional[bool]:
        lowered = value.lower()
        if any(word in lowered for word in ("instock", "in stock", "available")):
            return True
        if any(word in lowered for word in ("outofstock", "out of stock", "unavailable")):
            return False
        return None

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        for tag in soup.find_all(["h1", "h2"]):
            text = tag.get_text(strip=True)
            if text:
                return text
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return ""
