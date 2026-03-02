"""
SapphireScraper
--------------
Scrapes dress listings from sapphireonline.pk.
Utilizes HTML scraping for collection pages since Sapphire (Salesforce CC) 
doesn't expose the public Shopify products.json endpoint.
"""

import logging
from bs4 import BeautifulSoup

from app.models.schemas import DressItem
from app.services.scrapers.base import DressScraper

logger = logging.getLogger(__name__)


class SapphireScraper(DressScraper):
    """Concrete scraper for sapphireonline.pk — HTML Scraper."""

    CONFIG_KEY = "sapphire"

    def __init__(self) -> None:
        super().__init__(self.CONFIG_KEY)

    def scrape(self, gender: str, color_keywords: list[str]) -> list[DressItem]:
        handles: list[str] = self._cfg.get("gender_collections", {}).get(gender, [])
        seen_urls: set[str] = set()
        items: list[DressItem] = []

        sel = self._cfg["selectors"]

        for handle in handles:
            # Construct collection URL
            # e.g. https://pk.sapphireonline.pk/collections/ready-to-wear
            collection_url = f"{self._cfg['base_url'].rstrip('/')}/collections/{handle}"
            
            logger.info("[%s] Scraping HTML collection: %s", self._brand, collection_url)
            soup = self._get_html(collection_url)
            if not soup:
                continue

            # Pure HTML Scrape
            cards = soup.select(sel["product_card"])
            if not cards:
                logger.warning("[%s] No product cards found for handle: %s", self._brand, handle)
                continue

            for card in cards:
                # Name & URL
                name_el = card.select_one(sel["name"])
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                
                # Check color keywords if provided
                matched_color = None
                if color_keywords:
                    searchable = name.lower()
                    for kw in color_keywords:
                        if kw.lower() in searchable:
                            matched_color = kw
                            break
                    if not matched_color:
                        continue
                
                raw_url = name_el.get("href") if name_el.name == "a" else None
                if not raw_url:
                    # fallback to searching within the element
                    a_tag = name_el if name_el.name == "a" else name_el.find("a")
                    raw_url = a_tag.get("href") if a_tag else None
                
                product_url = self._full_url(raw_url)
                if not product_url or product_url in seen_urls:
                    continue

                # Price
                price = self._extract_text(card, sel["price"])

                # Image
                img_el = card.select_one(sel["image"])
                image_url = None
                if img_el:
                    image_url = self._full_url(img_el.get("src") or img_el.get("data-src"))

                seen_urls.add(product_url)
                items.append(DressItem(
                    brand=self._brand,
                    name=name,
                    gender=gender,
                    color=matched_color,
                    price=price,
                    url=product_url,
                    image_url=image_url
                ))

            # Stop if we found items for a handle (to keep it fast)
            if items:
                break

        # Fallback to search if collection was empty and keywords provided
        if not items and color_keywords:
            logger.info("[%s] Collection results empty. Trying HTML search.", self._brand)
            for kw in color_keywords:
                search_url = self._search_url(kw)
                soup = self._get_html(search_url)
                if not soup:
                    continue
                
                cards = soup.select(sel["product_card"])
                for card in cards:
                    name_el = card.select_one(sel["name"])
                    if not name_el: continue
                    name = name_el.get_text(strip=True)
                    
                    product_url = self._full_url(name_el.get("href"))
                    if not product_url or product_url in seen_urls:
                        continue
                    
                    price = self._extract_text(card, sel["price"])
                    img_el = card.select_one(sel["image"])
                    image_url = self._full_url(img_el.get("src")) if img_el else None
                    
                    seen_urls.add(product_url)
                    items.append(DressItem(
                        brand=self._brand, name=name, gender=gender,
                        color=kw, price=price, url=product_url, image_url=image_url
                    ))
                
                if len(items) >= 10:
                    break

        return items
