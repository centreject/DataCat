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


def load_catalog(path: Path = CATALOG_PATH) -> PurposeCatalog:
    return PurposeCatalog(json.loads(path.read_text(encoding="utf-8")))


CATALOG = load_catalog()
