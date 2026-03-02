"""
DressScraper — abstract base class
------------------------------------
All brand-specific scrapers inherit from this base.

Primary Strategy — Shopify Products JSON API
---------------------------------------------
Both supported brands (J. and Bonanza) are Shopify stores. Their
collection pages render products via JavaScript, so plain HTML scraping
returns nothing. Instead we call the publicly available Shopify endpoint:

    GET /collections/<handle>/products.json?limit=<N>&page=<P>

This returns real JSON data without needing a headless browser.

Fallback Strategy — Keyword Search (HTML)
-----------------------------------------
If all collection handles fail or return 0 products, the scraper falls
back to the Shopify search API:

    GET /search?q=<keyword>&type=product

The search page also renders via JS on the front-end, but the search
route on Shopify stores often includes product data inline in the HTML.
"""

import logging
from abc import ABC, abstractmethod
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from app.config.color_rules import SCRAPER_CONFIG
from app.models.schemas import DressItem

logger = logging.getLogger(__name__)


class DressScraper(ABC):
    """Abstract base class for all dress scrapers."""

    def __init__(self, config_key: str) -> None:
        cfg = SCRAPER_CONFIG.get(config_key)
        if cfg is None:
            raise ValueError(f"No scraper config found for key: '{config_key}'")
        self._cfg = cfg
        self._key = config_key
        self._brand: str = cfg["brand_name"]
        self._results_per_page: int = cfg["results_per_page"]
        self._max_pages: int = cfg.get("max_pages", 1)

    # ------------------------------------------------------------------
    # Abstract contract
    # ------------------------------------------------------------------

    @abstractmethod
    def scrape(self, gender: str, color_keywords: list[str]) -> list[DressItem]:
        """
        Scrape products for a given gender and filter by color keywords.

        Parameters
        ----------
        gender : str
            ``"men"`` or ``"women"``.
        color_keywords : list[str]
            Filter by these color names. Empty list → return everything.

        Returns
        -------
        list[DressItem]
        """

    # ------------------------------------------------------------------
    # Shopify JSON API helpers (primary strategy)
    # ------------------------------------------------------------------

    def _shopify_products_url(self, handle: str, page: int = 1) -> str:
        base = self._cfg["base_url"].rstrip("/")
        return (
            f"{base}/collections/{handle}/products.json"
            f"?limit={self._results_per_page}&page={page}"
        )

    def _fetch_shopify_products(self, handle: str) -> list[dict]:
        all_products: list[dict] = []
        for page in range(1, self._max_pages + 1):
            url = self._shopify_products_url(handle, page)
            try:
                response = requests.get(
                    url,
                    headers=self._cfg["headers"],
                    timeout=self._cfg["timeout"],
                )
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.warning("[%s] API request failed for %s: %s", self._brand, url, exc)
                break

            products = data.get("products", [])
            if not products:
                break
            all_products.extend(products)

        return all_products

    def _shopify_product_to_item(
        self,
        product: dict,
        gender: str,
        color_keywords: list[str],
    ) -> DressItem | None:
        """
        Convert a raw Shopify product dict to a ``DressItem``.
        Returns None if strict color keywords are provided and none match.
        """
        title: str = product.get("title", "").strip()
        if not title:
            return None

        tags: list[str] = [t.strip() for t in product.get("tags", [])]
        searchable_text = (title + " " + " ".join(tags)).lower()

        # Lenient matching: check if any keyword is a substring
        matched_color = None
        if color_keywords:
            for kw in color_keywords:
                if kw.lower() in searchable_text:
                    matched_color = kw
                    break
            
            # If no match found and we have color keywords, skip this item
            if not matched_color:
                return None

        # Price
        variants = product.get("variants", [])
        price: str | None = None
        if variants:
            try:
                p_val = float(variants[0].get("price", 0))
                price = f"PKR {p_val:,.0f}"
            except:
                price = str(variants[0].get("price"))

        # URL
        handle = product.get("handle", "")
        if not handle:
            return None
        product_url = f"{self._cfg['base_url'].rstrip('/')}/products/{handle}"

        # Image
        images = product.get("images", [])
        image_url: str | None = images[0].get("src") if images else None

        return DressItem(
            brand=self._brand,
            name=title,
            gender=gender,
            color=matched_color,
            price=price,
            url=product_url,
            image_url=image_url,
        )

    # ------------------------------------------------------------------
    # Shared HTTP helpers (used for fallback HTML search)
    # ------------------------------------------------------------------

    def _get_html(self, url: str) -> BeautifulSoup | None:
        try:
            response = requests.get(
                url,
                headers=self._cfg["headers"],
                timeout=self._cfg["timeout"],
            )
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as exc:
            logger.warning("[%s] HTML request failed for %s: %s", self._brand, url, exc)
            return None

    def _search_url(self, query: str) -> str:
        return self._cfg["search_url"].format(query=quote_plus(query))

    def _full_url(self, path: str | None) -> str | None:
        if not path:
            return None
        return path if path.startswith("http") else urljoin(self._cfg["base_url"], path)

    def _extract_text(self, tag, selector: str) -> str | None:
        el = tag.select_one(selector)
        return el.get_text(strip=True) if el else None
