"""
Central configuration: skin-tone → color palette mapping and per-brand scraper config.
Nothing is hardcoded in the service layer; all values live here.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Skin-tone enum — aligned with app/color_schems.txt
# ---------------------------------------------------------------------------

class SkinTone(str, Enum):
    LIGHT = "Light"
    LIGHT_MEDIUM = "Light-Medium"
    MEDIUM = "Medium"
    TAN = "Tan"
    DEEP = "Deep"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Skin-tone → HSV brightness thresholds (using Luma formula 0.299R+0.587G+0.114B)
# ---------------------------------------------------------------------------

SKIN_HSV_FILTER = {
    "saturation_min": 10,  # lowered from 15 for better detection
    "saturation_max": 180, 
    "value_min": 30,       # lowered for darker skin
    "value_max": 255,      # full range
}

# Values represent Luma (0-255) thresholds
SKIN_TONE_THRESHOLDS = {
    "LIGHT_MIN": 170,
    "LIGHT_MEDIUM_MIN": 140,
    "MEDIUM_MIN": 110,
    "TAN_MIN": 70,
    # Anything below 70 is DEEP
}


# ---------------------------------------------------------------------------
# Color palettes per skin tone (sourced from app/color_schems.txt)
# ---------------------------------------------------------------------------

COLOR_RULES: dict[str, list[str]] = {
    SkinTone.LIGHT: [
        "White", "Silver", "Black", "Cobalt Blue", "Deep Ruby", "Indigo", "Teal",
        "Coral", "Terra Cotta", "Goldenrod", "Olive Green", "Cream", "Tan",
        "Klein Blue", "Orange Red", "Forest Green", "Wine", "Sea Green",
        "Royal Blue", "Cadet Blue", "Light Sea Green", "Pale Violet Red", "Steel Blue",
    ],
    SkinTone.LIGHT_MEDIUM: [
        "Wheat", "Burlywood", "Antique White", "Warm Camel", "Dark Sea Green",
        "Chocolate", "Coral", "Mauve", "Slate Blue", "Medium Violet Red",
        "Dark Slate", "Royal Blue", "Pompeii Red", "Hunter Green", "Amethyst",
        "Navy", "Forest Green", "Rosy Brown", "Steel Blue", "Dark Olive", "Fawn",
    ],
    SkinTone.MEDIUM: [
        "Mustard", "Rust", "Burnt Orange", "Olive Drab", "Wheat", "Tan",
        "Burlywood", "Byzantium", "Dark Blue", "Crimson", "Oxford Blue",
        "Forest Green", "Dark Red", "Deep Pink", "Teal", "Sapphire", "Emerald",
        "Seafoam", "Camel", "Dark Olive", "Terracotta", "Dusty Teal",
    ],
    SkinTone.TAN: [
        "Gold", "Coral", "Warm Brown", "Cream", "Wheat", "Khaki", "Dark Khaki",
        "Dark Magenta", "Cobalt Blue", "Violet", "Medium Violet Red", "Cobalt",
        "Pumpkin", "Steel Blue", "Byzantium", "Bottle Green", "Sapphire Dark",
        "Turquoise", "Mint Tint", "Caramel", "Dark Olive Green", "Burnt Sienna", "Ivory",
    ],
    SkinTone.DEEP: [
        "Gold", "Bright Orange", "Electric Yellow", "Orange-Red", "Magenta",
        "Turquoise", "Pure White", "Pure Blue", "Indigo", "Amber", "Ochre",
        "Deep Teal", "Burgundy", "Cobalt Blue", "Dark Turquoise", "Spring Green", "Light Cyan",
    ],
    SkinTone.UNKNOWN: [
        "Black", "White", "Navy", "Mustard",
    ],
}


# ---------------------------------------------------------------------------
# Scraper configuration — Shopify JSON API mode
# ---------------------------------------------------------------------------

SCRAPER_CONFIG: dict[str, dict] = {
    "j_dot": {
        "brand_name": "J.",
        "base_url": "https://www.junaidjamshed.com",
        "gender_collections": {
            "women": ["stitched", "unstitched", "women-pret", "women-unstitched"],
            "men":   ["men", "men-stitched", "men-unstitched"],
        },
        "search_url": "https://www.junaidjamshed.com/search?q={query}&type=product",
        "results_per_page": 50,
        "max_pages": 1,
        "selectors": {
            "product_card": "div.product-item",
            "name":         "div.product-item__title",
            "price":        "span.price",
            "url_attr":     "a.product-item__image-wrapper",
            "image":        "img.product-item__primary-image",
            "next_page":    "a[rel='next']",
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        },
        "timeout": 15,
    },
    "bonanza": {
        "brand_name": "Bonanza Satrangi",
        "base_url": "https://www.bonanzasatrangi.com",
        "gender_collections": {
            "women": ["stitched", "unstitched", "pret", "women"],
            "men":   ["men", "men-unstitched"],
        },
        "search_url": "https://www.bonanzasatrangi.com/search?q={query}&type=product",
        "results_per_page": 50,
        "max_pages": 1,
        "selectors": {
            "product_card": "div.product-item",
            "name":         "div.product-item-meta__title",
            "price":        "span.price",
            "url_attr":     "a.product-item__image-wrapper",
            "image":        "img.product-item__primary-image",
            "next_page":    "a[rel='next']",
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        },
        "timeout": 15,
    },
    "sapphire": {
        "brand_name": "Sapphire",
        "base_url": "https://pk.sapphireonline.pk",
        "gender_collections": {
            "women": ["ready-to-wear", "unstitched"],
            "men":   ["mens-stitched", "mens-unstitched"],
        },
        "search_url": "https://pk.sapphireonline.pk/search?q={query}&type=product",
        "results_per_page": 50,
        "max_pages": 1, 
        "selectors": {
            "product_card": "div.product-tile",
            "name":         "div.pdp-link a.link",
            "price":        "span.price .sales .value",
            "url_attr":     "div.pdp-link a.link",
            "image":        "img.tile-image",
            "next_page":    "a.next-page",
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        },
        "timeout": 20,
    },
}
