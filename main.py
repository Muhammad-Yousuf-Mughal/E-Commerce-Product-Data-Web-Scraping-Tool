"""Command-line interface for the E-Commerce Compare Scraper.

Usage examples:
    python main.py --url "https://books.toscrape.com/catalogue/category/books/travel_2/index.html" --query travel
    python main.py --url "https://example.com/product/123" "https://example.com/product/456"
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from scraper.logger import setup_logging
from scraper.pipeline import scrape_products


def _print_summary(stats: dict) -> None:
    print("\n" + "=" * 60)
    print("SCRAPE SUMMARY")
    print("=" * 60)
    print(f"Total products:      {stats.get('total_products')}")
    print(f"Avg price:           {stats.get('avg_price')}")
    print(f"Min price:           {stats.get('min_price')}")
    print(f"Max price:           {stats.get('max_price')}")
    print(f"Most common rating:  {stats.get('most_common_rating')}")
    print(f"Available count:     {stats.get('available_count')}")
    print("=" * 60)


def _print_table(df: pd.DataFrame) -> None:
    display = df[
        [c for c in ["name", "price", "rating", "available", "category", "source_site", "url"] if c in df.columns]
    ]
    print("\nPRODUCTS")
    print(display.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="E-Commerce Product Compare Scraper")
    parser.add_argument("--url", nargs="+", required=True, help="Product and/or listing URLs")
    parser.add_argument("--query", default="", help="Optional keyword filter for products")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages per listing URL")
    parser.add_argument("--max-products", type=int, default=None, help="Stop after scraping this many products")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--base-name", default="products", help="Base filename for exports")
    args = parser.parse_args()

    setup_logging()
    print(f"Scraping {len(args.url)} URL(s)...")

    result = scrape_products(
        urls=args.url,
        product_query=args.query,
        max_pages=args.max_pages,
        max_products=args.max_products,
        min_delay=args.delay,
        output_dir=args.output,
        base_name=args.base_name,
        do_save=True,
        do_analyze=True,
        do_visualize=True,
    )

    stats = result.get("stats", {})
    products = result.get("products", [])
    failures = result.get("failures", [])

    _print_summary(stats)
    if products:
        _print_table(result["df"])

    if failures:
        print(f"\n[!] {len(failures)} URL(s) failed to scrape:")
        for f in failures:
            print(f"    - {f['url']}: {f['error']}")

    if result.get("csv"):
        print(f"\nSaved CSV:   {result['csv']}")
    if result.get("excel"):
        print(f"Saved Excel: {result['excel']}")
    if result.get("charts"):
        print("Saved charts:")
        for name, path in result["charts"].items():
            print(f"    - {name}: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
