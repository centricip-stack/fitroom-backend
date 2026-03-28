"""
Pydantic schemas for the Fashn-VTON API.

Keep this module free of FastAPI-specific imports so it can be used
in standalone scripts, tests, and the scraper layer without pulling
in the full FastAPI request machinery.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Try-on models (existing)
# ---------------------------------------------------------------------------

class TryOnRequest(BaseModel):
    category: Literal["tops", "bottoms", "one-pieces"]


class TryOnResponse(BaseModel):
    output_image_path: str


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


# ---------------------------------------------------------------------------
# Festival recommendation models  (NEW)
# ---------------------------------------------------------------------------

class FestivalProduct(BaseModel):
    """A ranked product returned inside festival_suggestions."""

    brand:      str
    name:       str
    gender:     Optional[Literal["men", "women"]] = None
    color:      Optional[str] = None
    price:      Optional[str] = None
    url:        str
    image_url:  Optional[str] = None
    ai_reason:  Optional[str] = None  # LLM explanation


class FestivalSuggestion(BaseModel):
    """Festival-aware product recommendations."""

    festival: str
    tradition: str
    title:    str
    days_away: Optional[int] = None
    products: list[FestivalProduct] = []


# ---------------------------------------------------------------------------
# Updated skin-analysis response  (EXTENDED — backward compatible)
# ---------------------------------------------------------------------------

class SkinAnalysisResponse(BaseModel):
    skin_tone:          str
    recommended_colors: list[str]
    suggested_dresses:  list[DressItem]
    total_results:      int
    saved_files:        list[str] = []
    # NEW — None when no upcoming festival is detected within the lookahead window
    festival_suggestions: Optional[FestivalSuggestion] = None