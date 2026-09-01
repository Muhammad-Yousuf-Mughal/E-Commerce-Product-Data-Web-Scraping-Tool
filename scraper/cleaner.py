"""Data cleaning: deduplication, name/price/rating normalisation."""

from __future__ import annotations

import re
from typing import List, Optional

import pandas as pd

from .extractors.base import Product
from .logger import get_logger

log = get_logger(__name__)

#: Promotional / boilerplate fragments often found in scraped titles.
_NOISE_WORDS = [
    "buy now",
    "shop now",
    "free shipping",
    "limited time",
    "special offer",
    "sale",
    "click here",
    "view details",
    "new arrival",
    "best seller",
]


def clean_name(name: str) -> str:
    """Normalise a product name: collapse whitespace and remove noise."""
    if not name:
        return ""
    text = name.strip()
    text = re.sub(r"\s+", " ", text)
    for word in _NOISE_WORDS:
        text = re.sub(rf"\b{re.escape(word)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def clean_price(value) -> Optional[float]:
    """Convert a price (str/num) to float, stripping symbols and commas."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("£", "").replace("€", "")
    text = text.replace("$", "")
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        return float(text)
    except ValueError:
        return None


def clean_rating(value) -> Optional[float]:
    """Normalise rating to a 0-5 float scale."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        rating = float(value)
    else:
        match = re.search(r"([\d.]+)", str(value))
        if not match:
            return None
        rating = float(match.group(1))
    if rating > 5:
        rating = rating / 2.0
    if rating < 0:
        rating = 0.0
    if rating > 5:
        rating = 5.0
    return round(rating, 1)


def _deduplicate(products: List[Product]) -> List[Product]:
    seen_urls: set = set()
    seen_names: set = set()
    deduped: List[Product] = []
    for product in products:
        url_key = (product.url or "").strip().lower()
        name_key = clean_name(product.name or "").lower()
        if url_key and url_key in seen_urls:
            log.debug("Dropping duplicate by URL: %s", product.url)
            continue
        if name_key and name_key in seen_names:
            log.debug("Dropping duplicate by name: %s", product.name)
            continue
        if url_key:
            seen_urls.add(url_key)
        if name_key:
            seen_names.add(name_key)
        deduped.append(product)
    return deduped


def clean_products(products: List[Product]) -> List[Product]:
    """Clean, normalise and deduplicate a list of products."""
    cleaned: List[Product] = []
    for product in products:
        product.name = clean_name(product.name)
        product.price = clean_price(product.price)
        product.rating = clean_rating(product.rating)
        if product.currency:
            product.currency = product.currency.upper()
        cleaned.append(product)

    deduped = _deduplicate(cleaned)
    log.info("Cleaned %d products -> %d after deduplication", len(cleaned), len(deduped))
    return deduped


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply normalisation to a DataFrame of scraped products."""
    if "name" in df.columns:
        df["name"] = df["name"].apply(clean_name)
    if "price" in df.columns:
        df["price"] = df["price"].apply(clean_price)
    if "rating" in df.columns:
        df["rating"] = df["rating"].apply(clean_rating)
    if "currency" in df.columns:
        df["currency"] = df["currency"].astype(str).str.upper()
    return df.drop_duplicates(subset=["url"]).reset_index(drop=True)
