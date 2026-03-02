"""
DataStore
---------
Persists scraped dress items to disk, organised by brand and gender.

Directory layout (relative to project root):
    data/
    ├── j_dot/
    │   ├── women_dresses_20260301_143000.json
    │   └── men_dresses_20260301_143000.json
    └── bonanza/
        ├── women_dresses_20260301_143000.json
        └── men_dresses_20260301_143000.json

Each JSON file is a list of DressItem dicts.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from app.models.schemas import DressItem, ScrapedDataSummary

logger = logging.getLogger(__name__)

# Root data directory — sits at the project root alongside `app/`
_DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


class DataStore:
    """
    Handles writing scraped dress items to brand-specific JSON files.

    Parameters
    ----------
    data_root : Path | None
        Override the default data directory (useful in tests).
    """

    def __init__(self, data_root: Path | None = None) -> None:
        self._root = data_root or _DATA_ROOT

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        brand_key: str,
        gender: str,
        items: list[DressItem],
    ) -> ScrapedDataSummary:
        """
        Serialise *items* to ``data/<brand_key>/<gender>_dresses_<ts>.json``.

        Parameters
        ----------
        brand_key : str
            Config key, e.g. ``"j_dot"`` or ``"bonanza"``.
        gender : str
            ``"men"`` or ``"women"``.
        items : list[DressItem]
            Scraped items from this brand/gender combination.

        Returns
        -------
        ScrapedDataSummary
            Metadata about the saved file.
        """
        brand_dir = self._root / brand_key
        brand_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{gender}_dresses_{timestamp}.json"
        file_path = brand_dir / filename

        payload = [item.model_dump() for item in items]
        file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            "DataStore saved %d items → %s",
            len(items),
            file_path,
        )

        return ScrapedDataSummary(
            brand=brand_key,
            gender=gender,
            item_count=len(items),
            file_path=str(file_path),
        )
