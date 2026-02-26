from __future__ import annotations

import re
from typing import Optional

from worlds.generic.Rules import set_rule
from BaseClasses import MultiWorld


_HERO_WIN_RE = re.compile(r"^Win a game as (.+?) \(Reward \d+/3\)$")


def hero_required_for_location(location_name: str) -> Optional[str]:
    m = _HERO_WIN_RE.match(location_name)
    if not m:
        return None
    return m.group(1).strip()


def set_deadlock_rules(multiworld: MultiWorld, player: int) -> None:
    for loc in multiworld.get_locations(player):
        hero = hero_required_for_location(loc.name)
        if hero:
            required_item = f"Unlock {hero}"
            set_rule(loc, lambda state, item=required_item: state.has(item, player))
