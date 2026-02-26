from __future__ import annotations

import csv
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


def load_locations() -> List[LocationDef]:
    with resources.files(__package__).joinpath("data/locations.csv").open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        locs: List[LocationDef] = []
        for row in reader:
            locs.append(LocationDef(name=row["location_name"].strip()))
        return locs


def build_location_name_to_id(base_id: int, location_defs: List[LocationDef]) -> Dict[str, int]:
    return {d.name: i for i, d in enumerate(location_defs, base_id)}
