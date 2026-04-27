"""Tiny backend i18n: error code -> localized message.

The frontend has its own message catalog; backend only needs to know the codes,
so localization at the API edge is optional. We expose ``message_for(code, locale)``
as a fallback for places that need a string in a server response.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"


@lru_cache(maxsize=8)
def _catalog(locale: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / "en.json"
    return json.loads(path.read_text(encoding="utf-8"))


def message_for(code: str, locale: str = "en") -> str:
    cat = _catalog(locale)
    return cat.get(code, cat.get("ERR_UNKNOWN", "An error occurred."))
