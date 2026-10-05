"""Purpose catalogue: the visit purposes the model may return, loaded from purposes.json.

The JSON is the single place to change when the event-classification plan changes
(names, descriptions, fallback keywords, delivery subtypes, LLM examples).
Order in the file is priority order.
"""

import json
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("purposes.json")


@dataclass(frozen=True)
class PurposeCatalog:
    raw: dict

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(p["id"] for p in self.raw["purposes"])

    @property
    def default(self) -> str:
        return self.raw["default"]

    @property
    def purposes(self) -> list[dict]:
        return self.raw["purposes"]

    @property
    def rules(self) -> list[str]:
        return self.raw["rules"]

    @property
    def few_shots(self) -> list[dict]:
        return self.raw["few_shots"]

    def get(self, purpose: str) -> dict:
        return next(p for p in self.purposes if p["id"] == purpose)

    def subtypes(self, purpose: str) -> tuple[str, ...]:
        return tuple(s["id"] for s in self.get(purpose).get("subtypes", []))

    def subtype_default(self, purpose: str) -> str | None:
        return self.get(purpose).get("subtype_default")

    def label(self, purpose: str, subtype: str | None = None) -> str:
        """Short Korean label the LLM writes (e.g. DELIVERY → 배송, PARCEL → 택배)."""
        if subtype is None:
            return self.get(purpose)["label"]
        return next(s["label"] for s in self.get(purpose).get("subtypes", []) if s["id"] == subtype)

    def purpose_id(self, text: str) -> str | None:
        """Purpose id from a label or an id (case-insensitive); None if unknown."""
        text = text.strip()
        return next((p["id"] for p in self.purposes if text == p["label"] or text.upper() == p["id"]), None)

    def subtype_id(self, purpose: str, text: str) -> str | None:
        text = text.strip()
        return next(
            (s["id"] for s in self.get(purpose).get("subtypes", []) if text == s["label"] or text.upper() == s["id"]),
            None,
        )


def load_catalog(path: Path = CATALOG_PATH) -> PurposeCatalog:
    return PurposeCatalog(json.loads(path.read_text(encoding="utf-8")))


CATALOG = load_catalog()
