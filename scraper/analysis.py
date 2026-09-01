"""Exploratory data analysis on scraped product data."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .logger import get_logger

log = get_logger(__name__)


def analyze_products(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute summary statistics and insights from a product DataFrame.

    Returns a dict of named metrics suitable for display or export.
    """
    stats: Dict[str, Any] = {}

    # Basic counts ------------------------------------------------------
    stats["total_products"] = int(len(df))

    numeric_prices = pd.to_numeric(df.get("price"), errors="coerce")
    valid_prices = numeric_prices.dropna()
    stats["products_with_price"] = int(valid_prices.count())
    stats["avg_price"] = float(valid_prices.mean()) if valid_prices.count() else None
    stats["min_price"] = float(valid_prices.min()) if valid_prices.count() else None
    stats["max_price"] = float(valid_prices.max()) if valid_prices.count() else None

    # Ratings -----------------------------------------------------------
    ratings = pd.to_numeric(df.get("rating"), errors="coerce").dropna()
    if ratings.count():
        stats["avg_rating"] = float(ratings.mean())
        stats["most_common_rating"] = float(ratings.mode().iloc[0])
    else:
        stats["avg_rating"] = None
        stats["most_common_rating"] = None

    # Availability ------------------------------------------------------
    if "available" in df.columns:
        available_series = df["available"].astype("boolean")
        stats["available_count"] = int(available_series.fillna(False).sum())
        stats["unavailable_count"] = int((~available_series.fillna(False)).sum())
    else:
        stats["available_count"] = 0
        stats["unavailable_count"] = 0

    # Categories --------------------------------------------------------
    if "category" in df.columns:
        category_counts = df["category"].value_counts()
        stats["category_counts"] = category_counts.to_dict()
    else:
        stats["category_counts"] = {}

    # Top products ------------------------------------------------------
    stats["top_rated"] = _top_rows(df, "rating", ascending=False, n=5)
    stats["cheapest"] = _top_rows(df, "price", ascending=True, n=5)
    stats["most_expensive"] = _top_rows(df, "price", ascending=False, n=5)

    log.info("Analysis complete: %d products", stats["total_products"])
    return stats


def _top_rows(df: pd.DataFrame, column: str, ascending: bool, n: int) -> list:
    if column not in df.columns:
        return []
    subset = df[[column, "name", "url"]].dropna(subset=[column])
    if subset.empty:
        return []
    top = subset.sort_values(column, ascending=ascending).head(n)
    return top.to_dict("records")
