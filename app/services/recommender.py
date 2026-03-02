"""
DressRecommender
----------------
Orchestrates the skin analysis -> brand recommendations flow.
Fetches real-time data from J. and Bonanza while pulling Sapphire results from MongoDB.
"""

import asyncio
import logging
from typing import List, Tuple

from app.models.schemas import DressItem
from app.services.scrapers.factory import ScraperFactory
from app.services.data_store import DataStore
from app.services.database import DatabaseService

logger = logging.getLogger(__name__)


class DressRecommender:
    """
    Combines skin-tone analysis with multi-brand scraping and database lookup.
    """

    def __init__(self) -> None:
        self._factory = ScraperFactory()
        self._db = DatabaseService()
        self._data_store = DataStore()

    async def recommend(self, skin_tone: str, gender: str, color_keywords: list[str]) -> Tuple[List[DressItem], List[str]]:
        """
        Coordinate scraping of J. and Bonanza (real-time) and pull Sapphire from MongoDB.
        
        Returns:
            (aggregated_items, list_of_saved_json_files)
        """
        logger.info("Recommending dresses for tone=%s gender=%s colors=%s", skin_tone, gender, color_keywords)

        # ---------------------------------------------------------
        # 1. Start real-time scraping (J. and Bonanza)
        # ---------------------------------------------------------
        brand_keys = ["j_dot", "bonanza"]
        realtime_tasks = []
        for key in brand_keys:
            scraper = self._factory.get_scraper_by_key(key)
            realtime_tasks.append(self._scrape_and_store_single(scraper, gender, color_keywords))

        # ---------------------------------------------------------
        # 2. Start database lookup (Sapphire)
        # ---------------------------------------------------------
        # We fetch Sapphire from MongoDB asynchronously
        db_task = self._db.get_dresses(brand="Sapphire", gender=gender)

        # ---------------------------------------------------------
        # 3. Wait for all sources
        # ---------------------------------------------------------
        # (realtime_results is list of (items, saved_path))
        results = await asyncio.gather(*realtime_tasks, db_task, return_exceptions=True)
        
        all_items: List[DressItem] = []
        saved_files: List[str] = []

        # Process real-time results (first len(brand_keys) elements)
        for i in range(len(brand_keys)):
            res = results[i]
            if isinstance(res, Exception):
                logger.error("Realtime scraper error: %s", res)
                # Fallback: Try fetching from DB if real-time fails
                fallback_items = await self._db.get_dresses(brand=SCRAPER_CONFIG[brand_keys[i]]["brand_name"], gender=gender)
                all_items.extend(self._filter_by_color(fallback_items, color_keywords))
                continue
            
            items, saved_path = res
            all_items.extend(items)
            if saved_path:
                saved_files.append(saved_path)

        # Process Sapphire DB results (last element)
        sapphire_res = results[-1]
        if isinstance(sapphire_res, list):
            # Filter DB results by color locally for accuracy
            filtered_sapphire = self._filter_by_color(sapphire_res, color_keywords)
            all_items.extend(filtered_sapphire)
            logger.info("Fetched %d Sapphire items from MongoDB.", len(filtered_sapphire))
        else:
            logger.error("Error fetching Sapphire from MongoDB: %s", sapphire_res)

        return all_items, saved_files

    async def _scrape_and_store_single(self, scraper, gender: str, color_keywords: list[str]) -> Tuple[List[DressItem], str]:
        """Runs a single scraper and persists it to local JSON disk."""
        try:
            items = scraper.scrape(gender, color_keywords)
            summary = self._data_store.save(scraper._key, gender, items)
            
            # Also asynchronously upsert these to MongoDB as a backup
            if items:
                asyncio.create_task(self._db.save_dress_items(items))
                
            return items, summary.file_path
        except Exception as e:
            logger.error("Scraping failed for %s: %s", scraper._brand, e)
            raise e

    def _filter_by_color(self, items: List[DressItem], color_keywords: List[str]) -> List[DressItem]:
        if not color_keywords:
            return items
            
        filtered = []
        for item in items:
            name_tags = (item.name + " " + (item.color or "")).lower()
            if any(kw.lower() in name_tags for kw in color_keywords):
                filtered.append(item)
        return filtered

# For circular dependency avoidance (SCRAPER_CONFIG is needed for fallback)
from app.config.color_rules import SCRAPER_CONFIG
