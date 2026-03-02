"""
app/services/scrapers/__init__.py

Public API for the scrapers package.
"""

from app.services.scrapers.base import DressScraper
from app.services.scrapers.factory import ScraperFactory

__all__ = ["DressScraper", "ScraperFactory"]
