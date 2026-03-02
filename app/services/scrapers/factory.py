"""
ScraperFactory
--------------
Creates and returns all available brand scrapers using a central registry.
"""

from app.services.scrapers.bonanza import BonanzaScraper
from app.services.scrapers.base import DressScraper
from app.services.scrapers.j_dot import JDotScraper
from app.services.scrapers.sapphire import SapphireScraper


class ScraperFactory:
    """
    Central registry of all available brand scrapers.
    """

    _MAPPING: dict[str, type[DressScraper]] = {
        "j_dot": JDotScraper,
        "bonanza": BonanzaScraper,
        "sapphire": SapphireScraper,
    }

    @staticmethod
    def get_all_scrapers() -> list[DressScraper]:
        """Return one instance of every configured scraper."""
        return [cls() for cls in ScraperFactory._MAPPING.values()]

    @staticmethod
    def get_scraper_by_key(key: str) -> DressScraper:
        """
        Return a single scraper by its config key.

        Parameters
        ----------
        key : str
            "j_dot", "bonanza", or "sapphire"

        Raises
        ------
        ValueError
            If *key* is not recognised.
        """
        cls = ScraperFactory._MAPPING.get(key)
        if cls is None:
            available_keys = list(ScraperFactory._MAPPING.keys())
            raise ValueError(f"Unknown scraper key: '{key}'. Available: {available_keys}")
        return cls()
