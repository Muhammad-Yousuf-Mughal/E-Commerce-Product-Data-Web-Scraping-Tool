"""Collect product URLs from category / search pages with pagination."""

from __future__ import annotations

import re
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http_client import HttpClient
from .logger import get_logger
from .robots import RobotsChecker

log = get_logger(__name__)

#: URL fragments commonly seen in product detail links.
_PRODUCT_HINT = re.compile(
    r"(/product[s]?/|/item[s]?/|/itm/|/dp/|/gp/|/p/|/products/|\.html|/book[s]?/|/_p/)",
    re.IGNORECASE,
)
_NEXT_HINTS = ["next", "next page", "›", "»"]


def _is_product_url(url: str) -> bool:
    """Heuristically decide whether a URL looks like a product detail page."""
    path = urlparse(url).path.lower()
    if _PRODUCT_HINT.search(path):
        return True
    return False


def _product_links(soup: BeautifulSoup, base_url: str) -> Set[str]:
    links: Set[str] = set()
    # Prefer product containers (e.g. <article class="product_pod"> on Books to Scrape)
    containers = soup.select("article.product_pod, [data-product], .product")
    if containers:
        for container in containers:
            for anchor in container.find_all("a", href=True):
                raw = anchor["href"]
                if raw.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                links.add(urljoin(base_url, raw))
        return links
    for anchor in soup.find_all("a", href=True):
        raw = anchor["href"]
        if raw.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, raw)
        if _is_product_url(absolute):
            links.add(absolute)
    return links


def _next_page_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    selectors = [
        "a.next",
        "a[rel='next']",
        ".paginator-next",
        ".pagination-next",
        "link[rel='next']",
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.get("href"):
            return urljoin(base_url, element["href"])
    # Fall back to text-based search.
    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(strip=True).lower()
        if any(hint in text for hint in _NEXT_HINTS):
            return urljoin(base_url, anchor["href"])
    return None


def collect_product_urls(
    start_url: str,
    max_pages: int = 5,
    max_products: Optional[int] = None,
    http_client: Optional[HttpClient] = None,
    robots: Optional[RobotsChecker] = None,
) -> List[str]:
    """Walk paginated category/search pages and collect product URLs.

    Args:
        start_url: The first category / search page to scrape.
        max_pages: How many subsequent pages to follow.
        max_products: Stop after collecting at most this many unique product URLs.
        http_client: Reuse an existing client (optional).
        robots: robots.txt checker (optional).

    Returns:
        A de-duplicated list of absolute product URLs.
    """
    client = http_client or HttpClient(min_delay=1.0)
    robots = robots or RobotsChecker(client)
    seen: Set[str] = set()
    current = start_url
    pages_visited = 0

    while current and pages_visited < max_pages:
        if not robots.can_fetch(current):
            log.warning("Skipping disallowed page: %s", current)
            break

        html = client.get_html(current)
        if not html:
            log.warning("No HTML returned for %s — stopping pagination", current)
            break

        soup = BeautifulSoup(html, "lxml")
        products = _product_links(soup, current)
        next_url = _next_page_url(soup, current)
        if next_url:
            products.discard(next_url)
        new_links = products - seen
        seen.update(new_links)
        log.info(
            "Page %d: found %d product links (%d new)",
            pages_visited + 1,
            len(products),
            len(new_links),
        )

        if max_products is not None and len(seen) >= max_products:
            log.info("Reached max_products=%d — stopping pagination", max_products)
            break

        pages_visited += 1
        current = next_url
        if current and current in seen:
            log.warning("Detected pagination loop at %s — stopping", current)
            break

    return list(seen)
