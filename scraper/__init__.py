"""
E-Commerce Product Data Web Scraper
====================================

A modular, user-driven web scraping application that collects product
information from e-commerce websites, cleans and validates the data, and
produces comparative analysis with visualisations.

Public API:
    scrape_products(urls, product_query=None, max_pages=N, ...)
"""

from .logger import get_logger, setup_logging
from .extractors.base import Product, ProductExtractor
from .extractors.registry import get_extractor_for_url
from .pagination import collect_product_urls
from .cleaner import clean_products
from .validator import validate_products
from .storage import save_csv, save_excel, save_products
from .analysis import analyze_products
from .visualization import create_charts
from .pipeline import scrape_products

__all__ = [
    "Product",
    "ProductExtractor",
    "get_logger",
    "setup_logging",
    "collect_product_urls",
    "clean_products",
    "validate_products",
    "save_csv",
    "save_excel",
    "save_products",
    "analyze_products",
    "create_charts",
    "get_extractor_for_url",
    "scrape_products",
]

__version__ = "1.0.0"
