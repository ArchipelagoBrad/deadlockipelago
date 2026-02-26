from __future__ import annotations

from BaseClasses import Region
from .locations import DeadlockLocation, LocationDef


def create_regions_and_locations(world, location_defs: list[LocationDef]) -> None:
    multiworld = world.multiworld
    player = world.player

    menu = Region("Menu", player, multiworld)
    main = Region("Main", player, multiworld)

    multiworld.regions += [menu, main]
    menu.connect(main)

    for d in location_defs:
        loc_id = world.location_name_to_id[d.name]
        main.locations.append(DeadlockLocation(player, d.name, loc_id, main))
