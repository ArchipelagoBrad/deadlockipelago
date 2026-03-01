from __future__ import annotations

import csv
import typing
from dataclasses import dataclass
from importlib import resources
from typing import Dict, List

from BaseClasses import Location


GAME_NAME = "Deadlock"


class DeadlockLocation(Location):
    game: str = GAME_NAME


@dataclass(frozen=True)
class LocationDef:
    name: str
    game_mode: str = ""  # "" = both, "standard", "street_brawl"


def load_locations() -> List[LocationDef]:
    with resources.files(__package__).joinpath("data/locations.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        locs: List[LocationDef] = []
        for row in reader:
            name = row["location_name"].strip()
            mode = (row.get("game_mode") or "").strip().lower()
            locs.append(LocationDef(name=name, game_mode=mode))
        return locs


def build_location_name_to_id(
    base_id: int,
    location_defs: List[LocationDef],
    filter_fn: typing.Callable[[LocationDef], bool] | None = None,
) -> Dict[str, int]:
    """Build name -> id. If filter_fn is set, only include defs that pass it; IDs use index in full list."""
    if filter_fn is None:
        return {d.name: base_id + i for i, d in enumerate(location_defs)}
    return {d.name: base_id + i for i, d in enumerate(location_defs) if filter_fn(d)}
