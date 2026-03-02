"""
Admin Routes
------------
Endpoints for administrative tasks, such as manual brand data synchronization.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.scrapers.factory import ScraperFactory
from app.services.database import DatabaseService
from app.models.schemas import ScrapedDataSummary

router = APIRouter(prefix="/admin", tags=["admin"])

logger = logging.getLogger(__name__)

db_service = DatabaseService()

async def perform_sync_sapphire():
    """Background task to scrape Sapphire and save to MongoDB."""
    logger.info("Starting background Sapphire sync...")
    try:
        scraper = ScraperFactory.get_scraper_by_key("sapphire")
        
        all_new_items = []
        for gender in ["men", "women"]:
            # Scrape everything for the sync (empty color filter)
            items = scraper.scrape(gender, [])
            all_new_items.extend(items)
            
        if all_new_items:
            count = await db_service.save_dress_items(all_new_items)
            logger.info("Sapphire sync complete. %d items updated in DB.", count)
        else:
            logger.warning("Sapphire sync: No items found to save.")
            
    except Exception as e:
        logger.error("Error during background Sapphire sync: %s", e)

@router.post("/sync-sapphire")
async def sync_sapphire(background_tasks: BackgroundTasks):
    """
    Trigger a manual scrape of Sapphire's collection and save results to MongoDB Atlas.
    Runs in the background to avoid blocking the API.
    """
    if db_service.client is None:
        raise HTTPException(
            status_code=503, 
            detail="Database not connected. Please check MONGODB_URI in your .env file."
        )
        
    background_tasks.add_task(perform_sync_sapphire)
    return {"message": "Sapphire synchronization started in the background."}
