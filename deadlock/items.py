from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib import resources
from typing import Dict, List, Optional

from BaseClasses import Item, ItemClassification


GAME_NAME = "Deadlock"

VICTORY_ITEM_NAME = "Victory"
# MacGuffin item: collect X to win (Spirits goal) or unlock final character (Win with Character).
# Spirits stay classified as filler in item definitions so they don't interfere with progression
# density, but we override DeadlockItem.excludable so Spirits are never placed in excluded
# locations.
FILLER_ITEM_NAME = "Spirits"


class DeadlockItem(Item):
    game: str = GAME_NAME

    @property
    def excludable(self) -> bool:  # type: ignore[override]
        # Treat Spirits (MacGuffin) as non-excludable even though they are filler-classified.
        # This ensures they can't be placed on user-excluded locations while keeping them
        # out of progression-balancing logic.
        if self.name == FILLER_ITEM_NAME:
            return False
        return super().excludable


@dataclass(frozen=True)
class ItemDef:
    name: str
    classification: ItemClassification
    copies: int
    include_in_filler: bool


def _parse_classification(value: str) -> ItemClassification:
    v = (value or "").strip().lower()
    match v:
        case "progression":
            return ItemClassification.progression
        case "useful":
            return ItemClassification.useful
        case "trap":
            return ItemClassification.trap
        case "filler":
            return ItemClassification.filler
        case _:
            # Default to filler if unknown, but better to be strict for dev:
            raise ValueError(f"Unknown item classification '{value}'")


def load_items() -> List[ItemDef]:
    # Works in source and in zipped apworld due to importlib.resources.
    with resources.files(__package__).joinpath("data/items.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        items: List[ItemDef] = []
        for row in reader:
            name = row["item_name"].strip()
            classification = _parse_classification(row.get("classification", "filler"))
            copies_raw = row.get("copies", "")
            copies = int(copies_raw) if str(copies_raw).strip() else 1
            include_in_filler = str(row.get("include_in_filler", "False")).strip().lower() == "true"
            items.append(ItemDef(name=name, classification=classification, copies=copies, include_in_filler=include_in_filler))
        return items


# Internal filler item used to pad itempool to location count when needed.
FILLER_ITEM_NAME = "Spirits"


def build_item_name_to_id(base_id: int, item_defs: list[ItemDef]) -> dict[str, int]:
    names = [d.name for d in item_defs]

    if FILLER_ITEM_NAME not in names:
        names.append(FILLER_ITEM_NAME)

    if VICTORY_ITEM_NAME not in names:
        names.append(VICTORY_ITEM_NAME)

    return {name: i for i, name in enumerate(names, base_id)}

