from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib import resources
from Options import Choice, Range, PerGameCommonOptions


def _load_hero_names() -> list[str]:
    """Hero names in order (matches heroes.csv; used for FinalCharacter option value -> name)."""
    names: list[str] = []
    try:
        pkg = __package__ or "deadlock"
        with resources.files(pkg).joinpath("data/heroes.csv").open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                names.append(row["name"].strip())
    except Exception:
        pass
    return names if names else ["Infernus"]


class GoalType(Choice):
    """How game completion is determined.

    - **Unique Characters:** Win with N different characters.
    - **Total Wins:** Win N matches total.
    - **Spirits:** Collect N Spirits (MacGuffin) to win.
    - **Win with Character:** Collect X Spirits to unlock your chosen final character, then win one match with that character.
    """
    display_name = "Goal Type"
    option_unique_characters = 0
    option_total_wins = 1
    option_spirits = 2
    option_win_with_character = 3
    default = 0


class UniqueCharactersToWin(Range):
    """Number of unique characters you must win with to finish (1-38)."""
    display_name = "Unique Characters to Win"
    range_start = 1
    range_end = 38
    default = 10


class TotalWinsToWin(Range):
    """Number of total match wins you must achieve to finish."""
    display_name = "Total Wins to Win"
    range_start = 1
    range_end = 100
    default = 25


class SpiritsToWin(Range):
    """Number of Spirits (MacGuffin) you must collect to finish. Max depends on game mode (Standard: 162, Street Brawl: 143)."""
    display_name = "Spirits to Win"
    range_start = 1
    range_end = 162  # Standard max; Street Brawl is clamped to 143 in world
    default = 10


class SpiritsToUnlockFinal(Range):
    """Number of Spirits (MacGuffin) you must collect to unlock your final character (Win with Character goal).

    The world caps this below the usual Spirits max by three: the final hero's three win checks require
    this many Spirits first and may themselves contain Spirits, so the threshold must be reachable using
    other locations only.
    """
    display_name = "Spirits to Unlock Final Character"
    range_start = 1
    range_end = 162
    default = 10


# Build FinalCharacter Choice from heroes.csv (option value = index into this list)
_FINAL_CHARACTER_NAMES: list[str] = _load_hero_names()


def _hero_name_to_option_key(name: str) -> str:
    return name.lower().replace(" ", "_").replace("&", "and")


# Build FinalCharacter with all option_* in the class namespace at creation time so the
# Choice metaclass (AssembleOptions) sees them and populates .options / .name_lookup.
_final_char_attrs: dict = {
    "__module__": __name__,
    "display_name": "Final Character (Win With)",
    "default": 0,
}
for _i, _name in enumerate(_FINAL_CHARACTER_NAMES):
    _final_char_attrs[f"option_{_hero_name_to_option_key(_name)}"] = _i

FinalCharacter = type("FinalCharacter", (Choice,), _final_char_attrs)


class GameMode(Choice):
    """Which game mode locations are included. Only checks for the selected mode exist in the seed."""
    display_name = "Game Mode"
    option_standard = 0
    option_street_brawl = 1
    default = 0


class ExcludeHardLocations(Choice):
    """When enabled, locations marked as hard (MVP/Key Player, high kills, fast rounds, etc.) are removed from the seed."""
    display_name = "Exclude Hard Locations"
    option_false = 0
    option_true = 1
    default = 0


@dataclass
class DeadlockOptions(PerGameCommonOptions):
    goal_type: GoalType
    unique_characters_to_win: UniqueCharactersToWin
    total_wins_to_win: TotalWinsToWin
    spirits_to_win: SpiritsToWin
    spirits_to_unlock_final: SpiritsToUnlockFinal
    final_character: FinalCharacter
    game_mode: GameMode
    exclude_hard_locations: ExcludeHardLocations
