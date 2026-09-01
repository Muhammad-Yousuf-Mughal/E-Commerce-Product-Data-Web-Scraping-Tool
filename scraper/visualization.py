"""Matplotlib visualisations for scraped product data."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .logger import get_logger

log = get_logger(__name__)


def _figure():
    return plt.subplots(figsize=(10, 6))


def plot_price_distribution(df: pd.DataFrame) -> tuple:
    """Histogram of product prices."""
    fig, ax = _figure()
    prices = pd.to_numeric(df.get("price"), errors="coerce").dropna()
    if prices.empty:
        ax.text(0.5, 0.5, "No price data", ha="center", va="center")
    else:
        ax.hist(prices, bins=min(30, max(5, len(prices))), edgecolor="black", alpha=0.7)
        ax.set_title("Product Price Distribution")
        ax.set_xlabel("Price")
        ax.set_ylabel("Frequency")
    fig.tight_layout()
    return fig


def plot_rating_distribution(df: pd.DataFrame) -> tuple:
    """Bar chart of rating frequency."""
    fig, ax = _figure()
    ratings = pd.to_numeric(df.get("rating"), errors="coerce").dropna()
    if ratings.empty:
        ax.text(0.5, 0.5, "No rating data", ha="center", va="center")
    else:
        counts = ratings.value_counts().sort_index()
        ax.bar(counts.index.astype(str), counts.values, edgecolor="black", alpha=0.7)
        ax.set_title("Rating Distribution")
        ax.set_xlabel("Rating")
        ax.set_ylabel("Count")
    fig.tight_layout()
    return fig


def plot_price_vs_rating(df: pd.DataFrame) -> tuple:
    """Scatter plot of price vs rating."""
    fig, ax = _figure()
    prices = pd.to_numeric(df.get("price"), errors="coerce")
    ratings = pd.to_numeric(df.get("rating"), errors="coerce")
    data = pd.DataFrame({"price": prices, "rating": ratings}).dropna()
    if data.empty:
        ax.text(0.5, 0.5, "No price/rating data", ha="center", va="center")
    else:
        ax.scatter(data["price"], data["rating"], alpha=0.6)
        ax.set_title("Price vs Rating")
        ax.set_xlabel("Price")
        ax.set_ylabel("Rating")
    fig.tight_layout()
    return fig


def plot_products_by_category(df: pd.DataFrame) -> tuple:
    """Bar chart of product counts per category."""
    fig, ax = _figure()
    if "category" not in df.columns or df["category"].isna().all():
        ax.text(0.5, 0.5, "No category data", ha="center", va="center")
    else:
        counts = df["category"].value_counts()
        ax.barh(counts.index.astype(str), counts.values, edgecolor="black", alpha=0.7)
        ax.set_title("Products by Category")
        ax.set_xlabel("Count")
    fig.tight_layout()
    return fig


def create_charts(df: pd.DataFrame, output_dir: Path | str = "output") -> Dict[str, Path]:
    """Generate all charts, save to ``output_dir``, return a mapping of names to paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    charts: Dict[str, tuple] = {
        "price_distribution": plot_price_distribution(df),
        "rating_distribution": plot_rating_distribution(df),
        "price_vs_rating": plot_price_vs_rating(df),
        "products_by_category": plot_products_by_category(df),
    }

    saved: Dict[str, Path] = {}
    for name, fig in charts.items():
        path = output_dir / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        saved[name] = path
        log.info("Saved chart: %s", path)

    return saved
