"""
FestivalService
---------------
Detects the nearest upcoming festival for a given region and datetime.

Uses a JSON calendar stored at app/data/festival_calendar.json.
The detection window is configurable (default: 60 days ahead),
so the service only surfaces festivals that are genuinely "upcoming".

Usage
-----
    from app.services.festival_service import FestivalService
    service = FestivalService()
    result = service.get_upcoming_festival(datetime.now(), region="Pakistan")
    # → {"festival": "Eid-ul-Fitr", "tradition": "Pakistani Traditional", "days_away": 13}
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Calendar file path (relative to this file's location)
# ---------------------------------------------------------------------------
_CALENDAR_PATH = Path(__file__).parent.parent / "data" / "festival_calendar.json"

# How many days ahead the festival must be to be considered "upcoming"
_LOOKAHEAD_DAYS = 60

# ---------------------------------------------------------------------------
# Tradition mapping — maps region → cultural tradition label used for
# product filtering downstream.
# ---------------------------------------------------------------------------
_REGION_TRADITION: dict[str, str] = {
    "Pakistan":     "Pakistani Traditional",
    "India":        "Indian Traditional",
    "Bangladesh":   "Bangladeshi Traditional",
    "UAE":          "Arab Traditional",
    "Saudi Arabia": "Arab Traditional",
    "Turkey":       "Turkish Traditional",
    "USA":          "Western",
    "UK":           "Western",
}

# ---------------------------------------------------------------------------
# Festival-specific tradition overrides
# When a festival's associated attire is more specific than the region default,
# override here.  Key = (region, festival_name) → tradition string.
# ---------------------------------------------------------------------------
_FESTIVAL_TRADITION_OVERRIDES: dict[tuple[str, str], str] = {
    ("Pakistan",  "Eid-ul-Fitr"):   "Pakistani Traditional - Eid",
    ("Pakistan",  "Eid-ul-Adha"):   "Pakistani Traditional - Eid",
    ("Pakistan",  "Ramadan"):       "Pakistani Traditional - Modest",
    ("India",     "Holi"):          "Indian Traditional - Festive",
    ("India",     "Diwali"):        "Indian Traditional - Festive",
    ("India",     "Navratri"):      "Indian Traditional - Festive",
    ("India",     "Baisakhi"):      "Indian Traditional - Festive",
    ("India",     "Durga Puja"):    "Indian Traditional - Festive",
    ("India",     "Ganesh Chaturthi"): "Indian Traditional - Festive",
    ("Bangladesh","Pohela Boishakh"): "Bangladeshi Traditional - Festive",
    ("UAE",       "Eid-ul-Fitr"):   "Arab Traditional - Eid",
    ("UAE",       "Eid-ul-Adha"):   "Arab Traditional - Eid",
    ("Saudi Arabia", "Eid-ul-Fitr"): "Arab Traditional - Eid",
    ("Saudi Arabia", "Eid-ul-Adha"): "Arab Traditional - Eid",
}


class FestivalService:
    """
    Stateless service — loads the calendar once at construction time.
    """

    def __init__(self, calendar_path: Optional[Path] = None) -> None:
        path = calendar_path or _CALENDAR_PATH
        try:
            with open(path, encoding="utf-8") as fh:
                self._calendar: dict[str, dict[str, str]] = json.load(fh)
            logger.info("Festival calendar loaded from %s", path)
        except FileNotFoundError:
            logger.error("Festival calendar not found at %s — festival detection disabled.", path)
            self._calendar = {}
        except json.JSONDecodeError as exc:
            logger.error("Festival calendar JSON parse error: %s", exc)
            self._calendar = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_upcoming_festival(
        self,
        now: datetime,
        region: str,
        lookahead_days: int = _LOOKAHEAD_DAYS,
    ) -> Optional[dict]:
        """
        Return the nearest upcoming festival for the given region within
        the lookahead window, or None if no festival is found.

        Parameters
        ----------
        now : datetime
            Current datetime (timezone-naive or timezone-aware).
        region : str
            Country / region name matching a top-level key in the calendar.
        lookahead_days : int
            How many calendar days ahead to search (default: 60).

        Returns
        -------
        dict | None
            {
                "festival":   "Eid-ul-Fitr",
                "tradition":  "Pakistani Traditional - Eid",
                "days_away":  13,
                "date":       "2026-03-20",
            }
            or None if no festival is found in the window.
        """
        region_festivals = self._calendar.get(region)
        if not region_festivals:
            logger.warning("No festivals found for region '%s'.", region)
            return None

        today = now.date() if hasattr(now, "date") else now
        deadline = today + timedelta(days=lookahead_days)

        nearest_festival: Optional[str] = None
        nearest_date: Optional[object] = None
        nearest_days: Optional[int] = None

        for festival_name, date_str in region_festivals.items():
            try:
                festival_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning("Invalid date '%s' for festival '%s'.", date_str, festival_name)
                continue

            if today <= festival_date <= deadline:
                days_away = (festival_date - today).days
                if nearest_days is None or days_away < nearest_days:
                    nearest_days = days_away
                    nearest_date = festival_date
                    nearest_festival = festival_name

        if nearest_festival is None:
            logger.info(
                "No upcoming festival in the next %d days for region '%s'.",
                lookahead_days, region,
            )
            return None

        tradition = _FESTIVAL_TRADITION_OVERRIDES.get(
            (region, nearest_festival),
            _REGION_TRADITION.get(region, "Traditional"),
        )

        result = {
            "festival":  nearest_festival,
            "tradition": tradition,
            "days_away": nearest_days,
            "date":      str(nearest_date),
        }
        logger.info(
            "Upcoming festival for '%s': %s in %d day(s) — tradition: %s",
            region, nearest_festival, nearest_days, tradition,
        )
        return result
