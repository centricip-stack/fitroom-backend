"""
DEPRECATED — this module is superseded by the modular `app.services.scrapers` package.

Left here as a compatibility shim. Any code importing from here will still work
because we re-export the same public names from the new package.
"""

# Re-export for backwards compatibility
from app.services.scrapers.base import DressScraper
from app.services.scrapers.factory import ScraperFactory
from app.services.scrapers.j_dot import JDotScraper
from app.services.scrapers.bonanza import BonanzaScraper

__all__ = ["DressScraper", "ScraperFactory", "JDotScraper", "BonanzaScraper"]
