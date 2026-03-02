"""
BonanzaScraper
--------------
Scrapes dress listings from bonanzasatrangi.com using the Shopify Products JSON API.
"""

import logging

from app.models.schemas import DressItem
from app.services.scrapers.base import DressScraper

logger = logging.getLogger(__name__)


class BonanzaScraper(DressScraper):
    """Concrete scraper for bonanza — Shopify JSON API."""

    CONFIG_KEY = "bonanza"

    def __init__(self) -> None:
        super().__init__(self.CONFIG_KEY)

    def scrape(self, gender: str, color_keywords: list[str]) -> list[DressItem]:
        handles: list[str] = self._cfg.get("gender_collections", {}).get(gender, [])
        seen_urls: set[str] = set()
        items: list[DressItem] = []

        for handle in handles:
            raw_products = self._fetch_shopify_products(handle)
            if not raw_products:
                continue

            for p in raw_products:
                item = self._shopify_product_to_item(p, gender, color_keywords)
                if item and item.url not in seen_urls:
                    seen_urls.add(item.url)
                    items.append(item)

            if items:
                break

        if not items and color_keywords:
            logger.info("[%s] Collection results empty. Trying HTML search for keywords.", self._brand)
            for kw in color_keywords:
                soup = self._get_html(self._search_url(kw))
                if not soup: continue
                
                sel = self._cfg["selectors"]
                cards = soup.select(sel["product_card"])
                for card in cards:
                    name = self._extract_text(card, sel["name"])
                    if not name: continue
                    
                    url_el = card.select_one(sel["url_attr"])
                    raw_url = url_el.get("href") if url_el else None
                    product_url = self._full_url(raw_url)
                    if not product_url or product_url in seen_urls:
                        continue
                    
                    img_el = card.select_one(sel["image"])
                    image_url = self._full_url(img_el.get("src") or img_el.get("data-src")) if img_el else None
                    
                    price = self._extract_text(card, sel["price"])
                    
                    seen_urls.add(product_url)
                    items.append(DressItem(
                        brand=self._brand, name=name, gender=gender,
                        color=kw, price=price, url=product_url, image_url=image_url
                    ))
                
                if len(items) >= 10: break

        return items
