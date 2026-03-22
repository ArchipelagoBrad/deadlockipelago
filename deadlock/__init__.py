from __future__ import annotations

import typing
from typing import Any, Mapping

from BaseClasses import Region, ItemClassification
from worlds.AutoWorld import World, WebWorld

from .options import (
    DeadlockOptions,
    GoalType,
    GameMode,
    ExcludeHardLocations,
    _FINAL_CHARACTER_NAMES,
)
from .items import DeadlockItem, load_items, build_item_name_to_id, FILLER_ITEM_NAME, VICTORY_ITEM_NAME
from .locations import DeadlockLocation, LocationDef, load_locations, build_location_name_to_id
from .rules import set_deadlock_rules
from .regions import create_regions_and_locations


class DeadlockWebWorld(WebWorld):
    # Required so WebHost knows what docs to show.
    tutorials = [("Setup Guide", "setup_en.md")]
    game_info_languages = ["en"]


class DeadlockWorld(World):
    game = "Deadlock"
    web = DeadlockWebWorld()
    options_dataclass = DeadlockOptions
    options: DeadlockOptions

    # Choose a stable, unique base_id range for your world.
    base_id = 512_000

    # These are populated at import time from CSV.
    _item_defs = load_items()
    _location_defs = load_locations()

    item_name_to_id = build_item_name_to_id(base_id, _item_defs)
    # location_name_to_id is set per-instance in generate_early from filtered defs (see below).
    location_name_to_id = build_location_name_to_id(base_id + 10_000, _location_defs)

    def create_item(self, name: str) -> DeadlockItem:
        # Determine classification from defs or fallback for special items.
        if name == FILLER_ITEM_NAME:
            # Spirits (MacGuffin) use filler classification in defs; DeadlockItem.excludable
            # is overridden so they are never placed on excluded locations.
            classification = ItemClassification.filler
        elif name == VICTORY_ITEM_NAME:
            classification = ItemClassification.progression
        else:
            d = next((x for x in self._item_defs if x.name == name), None)
            if d is None:
                raise KeyError(f"Unknown item '{name}'")
            classification = d.classification
        return DeadlockItem(name, classification, self.item_name_to_id.get(name), self.player)

    def create_event(self, name: str) -> DeadlockItem:
        # Event items have id=None (not part of item_name_to_id)
        return DeadlockItem(name, ItemClassification.progression, None, self.player)


    def _game_mode_value(self) -> str:
        """Return the game mode string for filtering locations (e.g. 'standard', 'street_brawl')."""
        if self.options.game_mode == GameMode.option_street_brawl:
            return "street_brawl"
        return "standard"

    def generate_early(self) -> None:
        mode = self._game_mode_value()
        exclude_hard = self.options.exclude_hard_locations == ExcludeHardLocations.option_true
        def mode_ok(d: LocationDef) -> bool:
            m = getattr(d, "game_mode", "") or ""
            return m == "" or m == mode
        def location_ok(d: LocationDef) -> bool:
            if not mode_ok(d):
                return False
            if exclude_hard and (getattr(d, "difficulty", "") or "").lower() == "hard":
                return False
            return True
        self._filtered_location_defs = [d for d in self._location_defs if location_ok(d)]
        self.location_name_to_id = build_location_name_to_id(
            self.base_id + 10_000, self._location_defs, filter_fn=location_ok
        )

    def create_regions(self) -> None:
        create_regions_and_locations(self, self._filtered_location_defs)

    def _max_spirits_placeable(self) -> int:
        """MacGuffin slots ~= non-Goal check locations (Goal holds locked Victory)."""
        return len(self._filtered_location_defs) - 1

    def _effective_spirits_to_unlock_final(self) -> int:
        """
        Spirits required before final character counts as unlocked (Win with Character).
        Capped so the threshold is reachable before opening that hero's three win checks
        (those checks may contain Spirits). Matches what we send in slot_data.
        """
        max_sp = self._max_spirits_placeable()
        v = min(self.options.spirits_to_unlock_final.value, max_sp)
        if self.options.game_mode == GameMode.option_street_brawl:
            v = min(v, 143)
        if self.options.goal_type == GoalType.option_win_with_character:
            v = min(v, max(1, max_sp - 3))
        return max(1, v)

    def _goal_location_name(self) -> str:
        if self.options.goal_type == GoalType.option_unique_characters:
            x = self.options.unique_characters_to_win.value
            return f"Goal: Win with {x} Unique Characters"
        if self.options.goal_type == GoalType.option_total_wins:
            x = self.options.total_wins_to_win.value
            return f"Goal: Win {x} Total Matches"
        if self.options.goal_type == GoalType.option_win_with_character:
            x = self.options.spirits_to_unlock_final.value
            hero = _FINAL_CHARACTER_NAMES[self.options.final_character.value] if self.options.final_character.value < len(_FINAL_CHARACTER_NAMES) else "?"
            return f"Goal: Win with {hero} (after {x} Spirits)"
        x = self.options.spirits_to_win.value
        return f"Goal: Collect {x} Spirits"

    def fill_slot_data(self) -> Mapping[str, Any]:
        """Data sent to the client in the Connected packet so /goal and win condition use the correct options."""
        # Max Spirits = number of check locations (pool size); Goal has locked Victory so pool size is locations - 1
        max_spirits = self._max_spirits_placeable()
        spirits_to_win = min(self.options.spirits_to_win.value, max_spirits)
        spirits_to_unlock_final = self._effective_spirits_to_unlock_final()
        final_character_index = self.options.final_character.value
        final_character_name = _FINAL_CHARACTER_NAMES[final_character_index] if final_character_index < len(_FINAL_CHARACTER_NAMES) else ""
        return {
            "goal_type": self.options.goal_type.value,
            "unique_characters_to_win": self.options.unique_characters_to_win.value,
            "total_wins_to_win": self.options.total_wins_to_win.value,
            "spirits_to_win": spirits_to_win,
            "spirits_to_unlock_final": spirits_to_unlock_final,
            "final_character": final_character_name,
            "game_mode": self.options.game_mode.value,
            "exclude_hard_locations": self.options.exclude_hard_locations.value,
        }

    def create_items(self) -> None:
        # Add all defined items with copies
        pool = []
        final_character_name = ""
        if self.options.goal_type == GoalType.option_win_with_character:
            idx = self.options.final_character.value
            if idx < len(_FINAL_CHARACTER_NAMES):
                final_character_name = _FINAL_CHARACTER_NAMES[idx]
        unlock_final_item = f"Unlock {final_character_name}" if final_character_name else ""
        for d in self._item_defs:
            if unlock_final_item and d.name == unlock_final_item:
                continue  # Do not add Unlock FinalCharacter to pool; player gets it when they reach X Spirits
            for _ in range(d.copies):
                pool.append(self.create_item(d.name))

        # Pad pool so total items = (locations - 1): Goal gets a locked Victory in set_rules, so it doesn't take from the pool.
        loc_count = len(self.multiworld.get_locations(self.player))
        fill_count = loc_count - 1
        if len(pool) < fill_count:
            pool += [self.create_item(FILLER_ITEM_NAME) for _ in range(fill_count - len(pool))]

        self.multiworld.itempool += pool

    def set_rules(self) -> None:
        set_deadlock_rules(self)

        goal_loc = self.multiworld.get_location("Goal", self.player)
        goal_loc.place_locked_item(self.create_item(VICTORY_ITEM_NAME))

        if self.options.goal_type == GoalType.option_spirits:
            # MacGuffin win: collect X Spirits. Allow Victory OR Spirits so the filler sees a reachable win (Victory at Goal).
            spirits_required = self.options.spirits_to_win.value
            if self.options.game_mode == GameMode.option_street_brawl:
                spirits_required = min(spirits_required, 143)
            self.multiworld.completion_condition[self.player] = (
                lambda state, p=self.player, req=spirits_required: (
                    state.has(VICTORY_ITEM_NAME, p) or state.has(FILLER_ITEM_NAME, p) >= req
                )
            )
        else:
            self.multiworld.completion_condition[self.player] = (
                lambda state: state.has(VICTORY_ITEM_NAME, self.player)
            )

# --- Launcher integration (0.6.6-compatible) ---

def _launch_deadlock_client(*args: str) -> None:
    from worlds import LauncherComponents
    from .Client import run_deadlock_client
    LauncherComponents.launch(run_deadlock_client, name="Deadlock Client", args=args)

def _register_deadlock_icon() -> str:
    """
    Register our icon with LauncherComponents using the apworld format so the launcher
    loads it from inside the apworld (no cache folder or filesystem extraction needed).
    See: LauncherComponents.py comment re "ap:module.name/path/to/file.png"
    """
    try:
        from worlds import LauncherComponents
    except ImportError:
        return "icon"  # fallback to default

    icon_key = "deadlock"
    if icon_key not in LauncherComponents.icon_paths:
        LauncherComponents.icon_paths[icon_key] = f"ap:{__name__}/icons/deadlock.png"
    return icon_key

def _register_launcher_component() -> None:
    try:
        from worlds.LauncherComponents import Component, components
    except ImportError:
        return

    components.append(Component(
        display_name="Deadlock Client",
        func=_launch_deadlock_client,
        game_name="Deadlock",
        supports_uri=True,
        description="Deadlock Archipelago client. Read the quickstart guide for setup instructions.",
        icon=_register_deadlock_icon(),
    ))

_register_launcher_component()