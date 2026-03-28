"""
RecommendationService
---------------------
Uses the Groq LLM (llama-3.3-70b-versatile) to rank a pre-filtered list
of festival-appropriate products and explain why each matches both the
upcoming festival and the user's skin tone.

IMPORTANT CONTRACT
------------------
* The LLM does **NOT** invent products.
* It only re-orders and annotates the product list it receives.
* If the Groq API is unavailable the service gracefully falls back to
  returning the products in their original order with a generic note.

Environment variables
---------------------
GROQ_API_KEY  – Groq API key (required for live ranking).
                Get yours at https://console.groq.com/keys

Usage
-----
    service = RecommendationService()
    ranked = await service.rank_for_festival(
        skin_tone="Medium",
        recommended_colors=["Mustard", "Rust"],
        region="Pakistan",
        festival_info={"festival": "Eid-ul-Fitr", "tradition": "Pakistani Traditional - Eid"},
        products=[DressItem(...)],
    )
"""

import asyncio
import json
import logging
import os
from typing import Optional

import requests  # sync HTTP — already in project deps; wrapped with asyncio.to_thread
from dotenv import load_dotenv

from app.models.schemas import DressItem

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq configuration
# ---------------------------------------------------------------------------
_GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
_GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL    = "llama-3.3-70b-versatile"
_REQUEST_TIMEOUT = 30  # seconds — sync requests timeout
_MAX_PRODUCTS_TO_LLM = 30  # cap to keep prompt size and latency manageable

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are an expert fashion stylist and cultural consultant for an ecommerce platform.
Your task is to rank a provided list of clothing products for a specific customer attending an upcoming cultural festival.

RULES (CRITICAL - DO NOT BREAK):
1. You MUST only rank products from the list provided. Do NOT invent or mention any products not in the list.
2. Return a JSON object with a single key "products" whose value is an array of ranked product objects.
3. Each object must preserve ALL original fields from the input exactly.
4. Add ONE extra field "ai_reason" (string, ≤ 25 words) explaining why the item suits the festival and skin tone.
5. Return ONLY the JSON object — no markdown, no prose, no code fences.
6. If no products are suitable, return {"products": []}.
"""

_USER_PROMPT_TEMPLATE = """Customer profile:
- Skin Tone: {skin_tone}
- Recommended Colors: {colors}
- Region: {region}
- Upcoming Festival: {festival}
- Cultural Tradition: {tradition}
- Days Until Festival: {days_away}

Available products (rank these from most to least suitable):
{products_json}

Respond with a JSON object only: {{"products": [...]}}"""


class RecommendationService:
    """
    Orchestrates festival product ranking via the Groq Chat Completions API.
    Network calls use the synchronous `requests` library wrapped with
    asyncio.to_thread so they don't block the FastAPI event loop.
    Gracefully degrades to a deterministic fallback on any error.
    """

    def __init__(self) -> None:
        if not _GROQ_API_KEY or _GROQ_API_KEY == "your_groq_api_key_here":
            logger.warning(
                "GROQ_API_KEY not configured — festival product ranking will use "
                "fallback ordering.  Set GROQ_API_KEY in app/.env to enable LLM ranking."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def rank_for_festival(
        self,
        skin_tone: str,
        recommended_colors: list[str],
        region: str,
        festival_info: dict,
        products: list[DressItem],
    ) -> list[dict]:
        """
        Rank *products* using the Groq LLM.

        Returns a list of plain dicts (DressItem fields + "ai_reason").
        Falls back to unranked products with a generic ai_reason on any error.
        """
        if not products:
            return []

        # Cap at max to keep prompt/latency reasonable
        products_to_rank = products[:_MAX_PRODUCTS_TO_LLM]

        api_key = os.getenv("GROQ_API_KEY", "")  # re-read at call time (supports hot-reload)
        if not api_key or api_key == "your_groq_api_key_here":
            return self._fallback(products_to_rank, festival_info.get("festival", ""))

        user_message = self._build_prompt(
            skin_tone=skin_tone,
            recommended_colors=recommended_colors,
            region=region,
            festival_info=festival_info,
            products=products_to_rank,
        )

        try:
            # Run blocking HTTP call in a thread pool so the event loop is free
            ranked = await asyncio.to_thread(self._call_groq_sync, api_key, user_message)
            logger.info(
                "Groq ranked %d festival products for %s / %s.",
                len(ranked), region, festival_info.get("festival"),
            )
            return ranked
        except Exception as exc:
            logger.error("Groq ranking failed (%s) — using fallback order.", exc)
            return self._fallback(products_to_rank, festival_info.get("festival", ""))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        skin_tone: str,
        recommended_colors: list[str],
        region: str,
        festival_info: dict,
        products: list[DressItem],
    ) -> str:
        """Build the user message string for the LLM."""
        products_json = json.dumps(
            [p.model_dump() for p in products],
            ensure_ascii=False,
            indent=2,
        )
        return _USER_PROMPT_TEMPLATE.format(
            skin_tone=skin_tone,
            colors=", ".join(recommended_colors),
            region=region,
            festival=festival_info.get("festival", ""),
            tradition=festival_info.get("tradition", ""),
            days_away=festival_info.get("days_away", "unknown"),
            products_json=products_json,
        )

    def _call_groq_sync(self, api_key: str, user_message: str) -> list[dict]:
        """
        Synchronous Groq API call (runs in thread pool via asyncio.to_thread).
        Raises on HTTP or JSON parse errors (caller handles gracefully).
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "model":    _GROQ_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            "temperature":     0.2,
            "max_tokens":      4096,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(
            _GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        data    = response.json()
        content = data["choices"][0]["message"]["content"]

        parsed = json.loads(content)

        # Prefer the "products" key returned by our prompt template
        if isinstance(parsed, list):
            return parsed
        for key in ("products", "ranked_products", "items", "results"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        # Last resort: pick the first list value found
        for value in parsed.values():
            if isinstance(value, list):
                return value

        logger.warning("Unexpected Groq response shape (%s) — using fallback.", list(parsed.keys()))
        raise ValueError(f"Cannot extract product list from Groq response: {list(parsed.keys())}")

    @staticmethod
    def _fallback(products: list[DressItem], festival: str) -> list[dict]:
        """
        Return products in their existing order with a generic ai_reason.
        Used when the API key is missing or any call to the LLM fails.
        """
        result = []
        for product in products:
            item = product.model_dump()
            item["ai_reason"] = (
                f"Recommended for {festival} based on color and style compatibility."
                if festival else "Recommended based on color and style compatibility."
            )
            result.append(item)
        return result
