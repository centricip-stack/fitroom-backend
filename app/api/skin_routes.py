"""
Skin Analysis API Route
-----------------------
POST /skin-analysis

Accepts a person image upload, analyzes skin tone via MediaPipe,
scrapes J. and Bonanza for matching dresses from their Men/Women
Dresses sections, persists results to disk, and returns a response.

Query parameters
----------------
gender : "men" | "women"   (default: "women")
    Which gender's dresses section to scrape.
"""

import logging
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models.schemas import SkinAnalysisResponse
from app.services.recommender import DressRecommender
from app.services.skin_analyzer import SkinAnalyzerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skin-analysis", tags=["Skin Analysis"])

# ---------------------------------------------------------------------------
# Singleton service instances (constructed once at import time)
# ---------------------------------------------------------------------------
_skin_analyzer = SkinAnalyzerService()
_recommender   = DressRecommender()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
}


def _validate_image(file: UploadFile) -> None:
    """
    Raise HTTPException(415) if the uploaded file is not a recognised image type.
    """
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported media type '{content_type}'. "
                "Please upload a valid image file (JPEG, PNG, WebP, etc.)."
            ),
        )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=SkinAnalysisResponse,
    summary="Analyze skin tone and recommend dresses",
    description=(
        "Upload a clear frontal face photo. The endpoint will:\n"
        "1. Detect the face using MediaPipe.\n"
        "2. Classify the skin tone (Fair / Wheatish / Dark).\n"
        "3. Map the tone to a complementary color palette.\n"
        "4. Scrape J. and Bonanza Men/Women Dresses sections for matching items.\n"
        "5. Save results to data/<brand>/<gender>_dresses_<timestamp>.json.\n"
        "6. Return the skin tone, color palette, suggested dresses, and saved file paths."
    ),
)
async def analyze_skin_and_recommend(
    person_image: UploadFile = File(
        ...,
        description="Person image (JPEG / PNG / WebP). Must clearly show the face.",
    ),
    gender: Literal["men", "women"] = Query(
        default="women",
        description="Which gender's dresses section to scrape (men | women).",
    ),
) -> SkinAnalysisResponse:
    """
    Skin analysis + gender-aware dress recommendation pipeline.
    """
    _validate_image(person_image)

    image_bytes = await person_image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    logger.info(
        "Received skin-analysis request (file=%s, gender=%s)",
        person_image.filename, gender,
    )

    # Step 1 — Skin tone detection
    skin_tone, recommended_colors = _skin_analyzer.analyze(image_bytes)
    logger.info("Detected skin_tone=%s, colors=%s", skin_tone, recommended_colors)

    # Step 2 — Gender-aware dress recommendation + data persistence
    suggested_dresses, saved_files = await _recommender.recommend(
        skin_tone=skin_tone,
        color_keywords=recommended_colors,
        gender=gender,
    )

    return SkinAnalysisResponse(
        skin_tone=skin_tone.value,
        recommended_colors=recommended_colors,
        suggested_dresses=suggested_dresses,
        total_results=len(suggested_dresses),
        saved_files=saved_files,
    )
