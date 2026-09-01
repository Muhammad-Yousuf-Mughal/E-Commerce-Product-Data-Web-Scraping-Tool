"""Core data model and extractor interface for product scraping."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Product:
    """A normalised product record scraped from an e-commerce page."""

    name: str = ""
    price: Optional[float] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    available: Optional[bool] = None
    availability: Optional[str] = None
    url: str = ""
    category: Optional[str] = None
    description: Optional[str] = None
    source_site: Optional[str] = None
    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Return the product as a plain dict for DataFrame construction."""
        return {
            "name": self.name,
            "price": self.price,
            "currency": self.currency,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "available": self.available,
            "availability": self.availability,
            "url": self.url,
            "category": self.category,
            "description": self.description,
            "source_site": self.source_site,
            "scraped_at": self.scraped_at,
        }


class ProductExtractor(ABC):
    """Interface implemented by site-specific extractors.

    Subclasses parse raw HTML and return a :class:`Product`. They may also
    declare which domains they are capable of handling via :meth:`can_handle`.
    """

    site_name: str = "generic"

    @abstractmethod
    def extract(self, html: str, url: str) -> Product:
        """Parse ``html`` fetched from ``url`` into a Product."""
        raise NotImplementedError

    def can_handle(self, url: str) -> bool:
        """Return True if this extractor applies to the given URL."""
        return False
