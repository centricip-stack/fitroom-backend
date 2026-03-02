"""
DatabaseService
---------------
Asynchronous MongoDB Atlas client using 'motor'.
Handles persistent storage for Sapphire results and fallback for J./Bonanza.
"""

import logging
import os
from typing import Any, List, Optional

import motor.motor_asyncio
from dotenv import load_dotenv

from app.models.schemas import DressItem

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MongoDB Configuration
# ---------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "fashn_vton")
COLLECTION_NAME = "dresses"


class DatabaseService:
    """
    Connects to MongoDB Atlas and provides methods to save/retrieve DressItems.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        if not MONGODB_URI:
            logger.warning("MONGODB_URI not found in environment. Database features will be disabled.")
            self.client = None
            self.db = None
            self.collection = None
        else:
            try:
                self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
                self.db = self.client[DATABASE_NAME]
                self.collection = self.db[COLLECTION_NAME]
                logger.info("Connected to MongoDB Atlas: %s", DATABASE_NAME)
                
                # Create indexes for faster lookup
                import asyncio
                # Note: Index creation is async, we don't block init
                # asyncio.create_task(self._create_indexes())
            except Exception as e:
                logger.error("Failed to connect to MongoDB: %s", e)
                self.client = None
                self.db = None
                self.collection = None

        self._initialized = True

    async def _create_indexes(self):
        if self.collection is not None:
            await self.collection.create_index([("brand", 1), ("gender", 1), ("color", 1)])
            await self.collection.create_index("url", unique=True)
            logger.info("MongoDB indexes verified.")

    async def save_dress_items(self, items: List[DressItem]) -> int:
        """
        Upsert a list of DressItems into the database.
        Returns the number of modified/inserted items.
        """
        if self.collection is None:
            logger.warning("Database not connected. Skipping save.")
            return 0

        if not items:
            return 0

        saved_count = 0
        for item in items:
            item_dict = item.model_dump()
            try:
                # Use URL as the unique identifier for upsert
                await self.collection.update_one(
                    {"url": item.url},
                    {"$set": item_dict},
                    upsert=True
                )
                saved_count += 1
            except Exception as e:
                logger.error("Error saving item to MongoDB (%s): %s", item.url, e)

        logger.info("Saved %d items to MongoDB.", saved_count)
        return saved_count

    async def get_dresses(self, brand: Optional[str] = None, gender: Optional[str] = None, color: Optional[str] = None) -> List[DressItem]:
        """
        Query dresses from the database with optional filters.
        """
        if self.collection is None:
            return []

        query = {}
        if brand:
            query["brand"] = brand
        if gender:
            query["gender"] = gender
        if color:
            # Case insensitive color match
            query["color"] = {"$regex": f"^{color}$", "$options": "i"}

        try:
            cursor = self.collection.find(query).limit(50)
            results = []
            async for doc in cursor:
                # Remove MongoDB _id before parsing to DressItem
                doc.pop("_id", None)
                results.append(DressItem(**doc))
            return results
        except Exception as e:
            logger.error("Error querying MongoDB: %s", e)
            return []
            
    async def get_all_brands(self) -> List[str]:
        if self.collection is None: return []
        return await self.collection.distinct("brand")
