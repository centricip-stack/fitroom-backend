"""
Pydantic schemas for the Fashn-VTON API.

Keep this module free of FastAPI-specific imports so it can be used
in standalone scripts, tests, and the scraper layer without pulling
in the full FastAPI request machinery.
"""

from typing import Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# [VTON - UNDER DEVELOPMENT] Try-on models
# Commented out while virtual try-on is under development.
# To re-enable: uncomment these classes AND re-enable vton_router in app/main.py
# ---------------------------------------------------------------------------

# class TryOnRequest(BaseModel):
#     category: Literal["tops", "bottoms", "one-pieces"]


# class TryOnResponse(BaseModel):
#     output_image_path: str


# ---------------------------------------------------------------------------
# Skin analysis models
# ---------------------------------------------------------------------------

class DressItem(BaseModel):
    """A single dress/garment result from a brand scraper."""

    brand:     str
    name:      str
    gender:    Optional[Literal["men", "women"]] = None
    color:     Optional[str] = None
    price:     Optional[str] = None
    url:       str
    image_url: Optional[str] = None


class ScrapedDataSummary(BaseModel):
    """Metadata about a completed scraping run saved to disk."""

    brand:      str
    gender:     str
    item_count: int
    file_path:  str


class SkinAnalysisResponse(BaseModel):
    skin_tone:         str
    recommended_colors: list[str]
    suggested_dresses: list[DressItem]
    total_results:     int
    saved_files:       list[str] = []
