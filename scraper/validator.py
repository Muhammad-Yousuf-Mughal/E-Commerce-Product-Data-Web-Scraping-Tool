"""Validation of scraped product records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from .extractors.base import Product
from .logger import get_logger

log = get_logger(__name__)


@dataclass
class ValidationResult:
    """Outcome of validating a single product."""

    url: str
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_product(product: Product) -> ValidationResult:
    """Check a product for required fields and consistency."""
    errors: List[str] = []
    warnings: List[str] = []

    if not product.name:
        errors.append("missing name")
    if product.price is None:
        errors.append("missing price")
    elif product.price < 0:
        errors.append("negative price")

    if product.url:
        if not product.url.startswith(("http://", "https://")):
            warnings.append("url missing scheme")

    if product.rating is not None and not (0 <= product.rating <= 5):
        warnings.append(f"rating out of range: {product.rating}")

    if product.available is None and not product.availability:
        warnings.append("availability unknown")

    is_valid = not errors
    return ValidationResult(
        url=product.url or "",
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
    )


def validate_products(products: List[Product]) -> List[Product]:
    """Return only products that pass validation, logging failures."""
    valid: List[Product] = []
    for product in products:
        result = validate_product(product)
        if result.is_valid:
            valid.append(product)
        else:
            log.warning("Invalid product %s: %s", product.url, "; ".join(result.errors))
    log.info("Validated %d products -> %d valid", len(products), len(valid))
    return valid


def validation_summary(products: List[Product]) -> dict:
    """Return aggregate validation statistics."""
    total = len(products)
    results = [validate_product(p) for p in products]
    valid = sum(1 for r in results if r.is_valid)
    errors = [e for r in results for e in r.errors]
    warnings = [w for r in results for w in r.warnings]
    return {
        "total": total,
        "valid": valid,
        "invalid": total - valid,
        "error_types": pd.Series(errors).value_counts().to_dict() if errors else {},
        "warning_types": pd.Series(warnings).value_counts().to_dict() if warnings else {},
    }
