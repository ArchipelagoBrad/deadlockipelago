from __future__ import annotations

import typing
from typing import Any, Mapping

from BaseClasses import Region, ItemClassification
from worlds.AutoWorld import World, WebWorld

from .options import DeadlockOptions, GoalType
from .items import DeadlockItem, load_items, build_item_name_to_id, FILLER_ITEM_NAME
from .items import VICTORY_ITEM_NAME
from .locations import DeadlockLocation, load_locations, build_location_name_to_id
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

    # These are populated at import time from CSV so datapackage can be built.
    _item_defs = load_items()
    _location_defs = load_locations()

    item_name_to_id = build_item_name_to_id(base_id, _item_defs)
    location_name_to_id = build_location_name_to_id(base_id + 10_000, _location_defs)

    def create_item(self, name: str) -> DeadlockItem:
        # Determine classification from defs or fallback for special items.
        if name == FILLER_ITEM_NAME:
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


    def create_regions(self) -> None:
        create_regions_and_locations(self, self._location_defs)

    def _goal_location_name(self) -> str:
        if self.options.goal_type == GoalType.option_unique_characters:
            x = self.options.unique_characters_to_win.value
            return f"Goal: Win with {x} Unique Characters"
        x = self.options.total_wins_to_win.value
        return f"Goal: Win {x} Total Matches"

    def fill_slot_data(self) -> Mapping[str, Any]:
        """Data sent to the client in the Connected packet so /goal and win condition use the correct options."""
        return {
            "goal_type": self.options.goal_type.value,
            "unique_characters_to_win": self.options.unique_characters_to_win.value,
            "total_wins_to_win": self.options.total_wins_to_win.value,
        }

    def create_items(self) -> None:
        # Add all defined items with copies
        pool = []
        for d in self._item_defs:
            for _ in range(d.copies):
                pool.append(self.create_item(d.name))

        # Pad pool to number of non-event locations (including goal)
        loc_count = len(self.multiworld.get_locations(self.player))
        if len(pool) < loc_count:
            pool += [self.create_item(FILLER_ITEM_NAME) for _ in range(loc_count - len(pool))]

        self.multiworld.itempool += pool

    def set_rules(self) -> None:
        set_deadlock_rules(self.multiworld, self.player)

        goal_loc = self.multiworld.get_location("Goal", self.player)
        goal_loc.place_locked_item(self.create_item(VICTORY_ITEM_NAME))

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
    0.6.6 LauncherComponents expects Component.icon to be a key in LauncherComponents.icon_paths,
    not a filepath. So we extract our PNG to a real file and register it.
    Returns the icon key to use (e.g. "deadlock").
    """
    try:
        from worlds import LauncherComponents
    except ImportError:
        return "icon"  # fallback to default

    icon_key = "deadlock"

    # Already registered?
    if icon_key in LauncherComponents.icon_paths:
        return icon_key

    # Pull bytes from inside the apworld (works with zipimport)
    import pkgutil
    data = pkgutil.get_data(__name__, "icons/deadlock.png")
    if not data:
        return "icon"

    # Write to a stable cache location
    import pathlib
    try:
        from Utils import user_path  # typical in AP builds
        out_dir = pathlib.Path(user_path("Cache", "apworld_icons"))
    except Exception:
        # fallback: current working dir
        out_dir = pathlib.Path(".") / "apworld_icons"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "deadlock.png"
    out_path.write_bytes(data)

    # Register key -> filesystem path
    LauncherComponents.icon_paths[icon_key] = str(out_path)
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
        description="Deadlock Archipelago client innit",
        icon=_register_deadlock_icon(),
    ))

_register_launcher_component()