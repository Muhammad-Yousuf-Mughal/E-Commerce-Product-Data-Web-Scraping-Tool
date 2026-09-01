"""End-to-end scraping pipeline orchestration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from .analysis import analyze_products
from .cleaner import clean_products
from .extractors.registry import get_extractor_for_url
from .http_client import HttpClient
from .logger import get_logger, setup_logging
from .pagination import collect_product_urls
from .robots import RobotsChecker
from .storage import save_products
from .validator import validate_products
from .visualization import create_charts

log = get_logger(__name__)


def _looks_like_product_page(url: str) -> bool:
    """Heuristic: a single URL is likely a product detail page, not a listing."""
    lowered = url.lower()
    # Standard e-commerce product URL markers.
    if any(
        marker in lowered
        for marker in ("/dp/", "/itm/", "/product/", "/products/", "/item/", "/gp/", "/p/")
    ):
        return True
    # Books to Scrape product slugs look like /catalogue/<name>_<id>/index.html
    # while listing/category pages contain "/category/" in the path.
    if "/category/" not in lowered and re.search(r"/[a-z0-9-]+_\d+/", lowered):
        return True
    return False


def scrape_products(
    urls: List[str],
    product_query: str = "",
    output_dir: str = "output",
    base_name: str = "products",
    max_pages: int = 5,
    max_products: Optional[int] = None,
    do_save: bool = True,
    do_analyze: bool = True,
    do_visualize: bool = True,
    min_delay: float = 1.0,
) -> dict:
    """Scrape product data, clean it, and produce analysis + exports.

    Args:
        urls: Product URLs and/or category/search URLs.
        product_query: Optional keyword to filter scraped products by name.
        output_dir: Directory for exports and charts.
        base_name: Base filename for CSV/Excel outputs.
        max_pages: Max pages to follow per listing URL.
        max_products: Stop after scraping at most this many products.
        do_save: Save CSV/Excel outputs.
        do_analyze: Compute summary statistics.
        do_visualize: Generate charts.
        min_delay: Minimum delay between requests per domain.

    Returns:
        Dict containing products, DataFrame, stats, chart paths and file paths.
    """
    setup_logging()
    client = HttpClient(min_delay=min_delay)
    robots = RobotsChecker(client)

    product_urls: List[str] = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        if not robots.can_fetch(url):
            log.warning("robots.txt disallows %s — skipping", url)
            continue
        if _looks_like_product_page(url):
            product_urls.append(url)
        else:
            found = collect_product_urls(
                url,
                max_pages=max_pages,
                max_products=max_products,
                http_client=client,
                robots=robots,
            )
            log.info("Collected %d product URLs from %s", len(found), url)
            product_urls.extend(found)

    # De-duplicate across all sources.
    product_urls = list(dict.fromkeys(product_urls))
    if max_products is not None and len(product_urls) > max_products:
        product_urls = product_urls[:max_products]
        log.info("Truncated to %d product URLs (max_products=%d)", len(product_urls), max_products)
    log.info("Scraping %d unique product URLs", len(product_urls))

    # Scrape each product, continuing past failures.
    products = []
    failures = []
    for index, url in enumerate(product_urls, start=1):
        html = client.get_html(url)
        if not html:
            failures.append({"url": url, "error": "request returned no HTML"})
            continue
        try:
            extractor = get_extractor_for_url(url)
            product = extractor.extract(html, url)
            products.append(product)
        except Exception as exc:  # noqa: BLE001 - continue on per-product errors
            log.exception("Error extracting product from %s", url)
            failures.append({"url": url, "error": str(exc)})

    # Apply product query filter.
    if product_query:
        q = product_query.strip().lower()
        products = [p for p in products if q in p.name.lower() or q in (p.description or "").lower()]

    # Clean + validate.
    products = clean_products(products)
    products = validate_products(products)

    result: dict = {"products": products, "failures": failures}

    if do_save:
        saved = save_products(products, output_dir=output_dir, base_name=base_name)
        result.update(saved)

    if do_analyze:
        df = _products_df(products)
        result["stats"] = analyze_products(df)
        result["df"] = df

    if do_visualize:
        df = _products_df(products)
        result["charts"] = create_charts(df, output_dir=Path(output_dir) / "charts")

    return result


def _products_df(products):
    from .storage import products_to_dataframe

    return products_to_dataframe(products)
