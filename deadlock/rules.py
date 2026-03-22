from __future__ import annotations

import re
from typing import Optional

from worlds.generic.Rules import set_rule, add_item_rule

from .items import FILLER_ITEM_NAME
from .options import GoalType, _FINAL_CHARACTER_NAMES


_HERO_WIN_RE = re.compile(r"^Win a game as (.+?) \(Reward \d+/3\)$")


def hero_required_for_location(location_name: str) -> Optional[str]:
    m = _HERO_WIN_RE.match(location_name)
    if not m:
        return None
    return m.group(1).strip()


def set_deadlock_rules(world) -> None:
    """Apply location access rules. ``world`` is the DeadlockWorld instance."""
    multiworld = world.multiworld
    player = world.player
    final_hero_name = ""
    if world.options.goal_type == GoalType.option_win_with_character:
        idx = world.options.final_character.value
        if idx < len(_FINAL_CHARACTER_NAMES):
            final_hero_name = _FINAL_CHARACTER_NAMES[idx]
    spirits_gate = world._effective_spirits_to_unlock_final()

    for loc in multiworld.get_locations(player):
        hero = hero_required_for_location(loc.name)
        if not hero:
            continue
        required_unlock = f"Unlock {hero}"
        if final_hero_name and hero == final_hero_name:
            # Final character is not in the item pool; client unlocks them after enough Spirits.
            set_rule(
                loc,
                lambda state, p=player, req=spirits_gate, macguffin=FILLER_ITEM_NAME: state.has(macguffin, p) >= req,
            )
        else:
            set_rule(loc, lambda state, item=required_unlock, p=player: state.has(item, p))
        # Prevent Unlock [Hero] from being placed in this hero's win locations,
        # so the hero is never locked behind their own checks.
        add_item_rule(loc, lambda item, unlock_name=required_unlock: item.name != unlock_name)
