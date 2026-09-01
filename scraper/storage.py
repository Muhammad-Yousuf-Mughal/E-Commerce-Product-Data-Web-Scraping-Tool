"""Storage of scraped products to CSV and Excel files."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from .extractors.base import Product
from .logger import get_logger

log = get_logger(__name__)

#: Standard column order for the exported dataset.
COLUMNS = [
    "name",
    "price",
    "currency",
    "rating",
    "rating_count",
    "available",
    "availability",
    "url",
    "category",
    "description",
    "source_site",
    "scraped_at",
]


def products_to_dataframe(products: List[Product]) -> pd.DataFrame:
    """Convert a list of products into a tidy DataFrame."""
    records = [product.to_dict() for product in products]
    df = pd.DataFrame(records)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[COLUMNS]


def save_csv(df: pd.DataFrame, path: Path | str) -> Path:
    """Save a DataFrame to CSV (UTF-8, one header row)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info("Saved CSV: %s", path)
    return path


def save_excel(
    df: pd.DataFrame,
    path: Path | str,
    sheet_name: str = "Products",
) -> Path:
    """Save a DataFrame to an Excel workbook with a single sheet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    log.info("Saved Excel: %s", path)
    return path


def save_products(
    products: List[Product],
    output_dir: Path | str = "output",
    base_name: str = "products",
) -> dict:
    """Save products to both CSV and Excel in ``output_dir``."""
    df = products_to_dataframe(products)
    output_dir = Path(output_dir)
    csv_path = save_csv(df, output_dir / f"{base_name}.csv")
    excel_path = save_excel(df, output_dir / f"{base_name}.xlsx")
    return {"df": df, "csv": csv_path, "excel": excel_path}
