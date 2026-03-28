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
region : str               (default: "Pakistan")
    User's country/region for festival detection and cultural recommendations.
"""

import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models.schemas import FestivalProduct, FestivalSuggestion, SkinAnalysisResponse
from app.services.festival_service import FestivalService
from app.services.recommendation_service import RecommendationService
from app.services.recommender import DressRecommender
from app.services.skin_analyzer import SkinAnalyzerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skin-analysis", tags=["Skin Analysis"])

# ---------------------------------------------------------------------------
# Singleton service instances (constructed once at import time)
# ---------------------------------------------------------------------------
_skin_analyzer      = SkinAnalyzerService()
_recommender        = DressRecommender()
_festival_svc       = FestivalService()
_recommendation_svc = RecommendationService()


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
        "1. Detect the face using OpenCV Haar cascade.\n"
        "2. Classify the skin tone (Light / Light-Medium / Medium / Tan / Deep).\n"
        "3. Map the tone to a complementary color palette.\n"
        "4. Scrape J. and Bonanza Men/Women Dresses sections for matching items.\n"
        "5. Save results to data/<brand>/<gender>_dresses_<timestamp>.json.\n"
        "6. Return the skin tone, color palette, suggested dresses, and saved file paths.\n"
        "7. (NEW) Detect the nearest upcoming festival for the given region and return "
        "   festival-aware ranked product suggestions via the Groq LLM."
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
    region: str = Query(
        default="Pakistan",
        description=(
            "User's country / region for festival detection "
            "(e.g. Pakistan, India, UAE, USA). "
            "Defaults to 'Pakistan'."
        ),
    ),
) -> SkinAnalysisResponse:
    """
    Skin analysis + gender-aware dress recommendation pipeline (festival-enhanced).

    Existing behaviour (Steps 1–2) is completely untouched.
    Steps 3–6 are new and isolated in a try/except so any failure there
    never breaks the core recommendation response.
    """
    _validate_image(person_image)

    image_bytes = await person_image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    logger.info(
        "Received skin-analysis request (file=%s, gender=%s, region=%s)",
        person_image.filename, gender, region,
    )

    # -----------------------------------------------------------------------
    # Step 1 — Skin tone detection  [EXISTING — UNCHANGED]
    # -----------------------------------------------------------------------
    skin_tone, recommended_colors = _skin_analyzer.analyze(image_bytes)
    logger.info("Detected skin_tone=%s, colors=%s", skin_tone, recommended_colors)

    # -----------------------------------------------------------------------
    # Step 2 — Gender-aware dress recommendation + data persistence [EXISTING — UNCHANGED]
    # -----------------------------------------------------------------------
    suggested_dresses, saved_files = await _recommender.recommend(
        skin_tone=skin_tone,
        color_keywords=recommended_colors,
        gender=gender,
    )

    # -----------------------------------------------------------------------
    # Steps 3–6 — Festival enrichment  [NEW — non-breaking]
    # Wrapped in try/except: failure here NEVER crashes the existing response.
    # -----------------------------------------------------------------------
    festival_suggestions: Optional[FestivalSuggestion] = await _build_festival_suggestions(
        skin_tone=skin_tone,
        recommended_colors=recommended_colors,
        region=region,
        suggested_dresses=suggested_dresses,
    )

    # -----------------------------------------------------------------------
    # Step 7 — Build and return response  [EXTENDED — backward compatible]
    # festival_suggestions is None when no upcoming festival is found.
    # -----------------------------------------------------------------------
    return SkinAnalysisResponse(
        skin_tone=skin_tone.value,
        recommended_colors=recommended_colors,
        suggested_dresses=suggested_dresses,
        total_results=len(suggested_dresses),
        saved_files=saved_files,
        festival_suggestions=festival_suggestions,
    )


# ---------------------------------------------------------------------------
# Festival enrichment — private async helper
# ---------------------------------------------------------------------------

async def _build_festival_suggestions(
    skin_tone,
    recommended_colors: list[str],
    region: str,
    suggested_dresses: list,
) -> Optional[FestivalSuggestion]:
    """
    Orchestrates Steps 3–6:
      3. Detect nearest upcoming festival for the region.
      4. Filter the already-fetched product list by tradition/region keywords.
      5. Send the filtered list to the Groq LLM for ranking.
      6. Return a FestivalSuggestion object (or None on any error).
    """
    try:
        # Step 3 — Festival detection
        now = datetime.now()
        festival_info = _festival_svc.get_upcoming_festival(now=now, region=region)

        if not festival_info:
            logger.info(
                "No upcoming festival detected for region '%s' — skipping festival step.",
                region,
            )
            return None

        festival_name = festival_info["festival"]
        tradition     = festival_info["tradition"]
        days_away     = festival_info.get("days_away")

        # Step 4 — Festival product filtering
        tradition_keywords = _extract_keywords(tradition, region, festival_name)
        festival_candidates = _filter_festival_products(
            products=suggested_dresses,
            color_keywords=recommended_colors,
            tradition_keywords=tradition_keywords,
        )
        if not festival_candidates:
            # Fallback: LLM gets the full list and picks the most suitable items
            logger.info(
                "Festival keyword filter returned 0 products; using full suggested_dresses (%d items).",
                len(suggested_dresses),
            )
            festival_candidates = suggested_dresses

        # Step 5 — Groq LLM ranking
        skin_tone_str = skin_tone.value if hasattr(skin_tone, "value") else str(skin_tone)

        ranked_dicts = await _recommendation_svc.rank_for_festival(
            skin_tone=skin_tone_str,
            recommended_colors=recommended_colors,
            region=region,
            festival_info=festival_info,
            products=festival_candidates,
        )

        # Coerce raw dicts to FestivalProduct (adds ai_reason, validates schema)
        ranked_products: list[FestivalProduct] = []
        for item_dict in ranked_dicts:
            try:
                ranked_products.append(FestivalProduct(**item_dict))
            except Exception as exc:
                logger.warning(
                    "Skipping malformed ranked product dict %s — %s",
                    item_dict, exc,
                )

        # Step 6 — Assemble FestivalSuggestion
        suggestion = FestivalSuggestion(
            festival=festival_name,
            tradition=tradition,
            title=f"Recommended for upcoming festival: {festival_name}",
            days_away=days_away,
            products=ranked_products,
        )

        logger.info(
            "Festival suggestions built: festival=%s, products=%d",
            festival_name, len(ranked_products),
        )
        return suggestion

    except Exception as exc:
        logger.error(
            "Festival enrichment failed (non-fatal): %s",
            exc, exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Festival filtering helpers  (module-private)
# ---------------------------------------------------------------------------

def _extract_keywords(tradition: str, region: str, festival: str) -> list[str]:
    """
    Build a deduplicated list of apparel keywords for the given
    festival + region combination, used to pre-filter products before
    sending them to the LLM.
    """
    keywords: list[str] = []

    # Festival-specific apparel keywords
    _festival_keywords: dict[str, list[str]] = {
        "Eid-ul-Fitr":          ["kameez", "kurta", "shalwar", "lawn", "embroidered", "festive", "eid"],
        "Eid-ul-Adha":          ["kameez", "kurta", "shalwar", "embroidered", "qurbani"],
        "Ramadan":              ["modest", "kameez", "lawn", "linen"],
        "Holi":                 ["colorful", "floral", "cotton", "festive"],
        "Diwali":               ["festive", "embroidered", "silk", "ethnic"],
        "Navratri":             ["ghagra", "chaniya", "choli", "festive", "colorful"],
        "Baisakhi":             ["phulkari", "festive", "colorful", "traditional"],
        "Pohela Boishakh":      ["festive", "traditional", "cotton"],
        "Independence Day":     ["green", "white", "national"],
        "Christmas":            ["festive", "formal", "party"],
        "Thanksgiving":         ["casual", "warm", "cozy"],
        "Halloween":            ["dark", "costume"],
        "Ganesh Chaturthi":     ["festive", "ethnic", "traditional"],
        "Durga Puja":           ["festive", "ethnic", "traditional"],
        "Onam":                 ["traditional", "festive"],
        "National Day":         ["traditional", "formal", "national"],
        "Basant":               ["yellow", "colorful", "festive"],
        "Shab-e-Barat":         ["modest", "traditional", "kameez"],
        "Al Isra Wal Miraj":    ["modest", "traditional"],
        "Republic Day":         ["formal", "traditional", "national"],
    }
    keywords.extend(_festival_keywords.get(festival, []))

    # Region-level generic apparel terms
    _region_keywords: dict[str, list[str]] = {
        "Pakistan":     ["kameez", "shalwar", "kurta", "lawn", "linen"],
        "India":        ["kurta", "salwar", "lehenga", "saree", "ethnic"],
        "Bangladesh":   ["sari", "kameez", "panjabi"],
        "UAE":          ["abaya", "kandura", "thobe", "modest"],
        "Saudi Arabia": ["abaya", "thobe", "modest"],
    }
    keywords.extend(_region_keywords.get(region, []))

    return list(dict.fromkeys(keywords))  # deduplicate, preserve order


def _filter_festival_products(
    products,
    color_keywords: list[str],
    tradition_keywords: list[str],
) -> list:
    """
    Soft filter: include a product if its name or color field contains
    at least one tradition keyword OR one recommended color keyword.
    Deliberately lenient — the LLM is the final arbiter of relevance.
    """
    if not tradition_keywords:
        return products

    results = []
    for item in products:
        haystack = ((item.name or "") + " " + (item.color or "")).lower()
        if any(kw.lower() in haystack for kw in tradition_keywords) or \
           any(kw.lower() in haystack for kw in color_keywords):
            results.append(item)

    return results
