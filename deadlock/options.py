from __future__ import annotations

from dataclasses import dataclass
from Options import Choice, Range, PerGameCommonOptions


class GoalType(Choice):
    """How game completion is determined.

    - **Unique Characters:** Win with N different characters.
    - **Total Wins:** Win N matches total.
    - **Spirits:** Collect N Spirits (MacGuffin) to win.
    """
    display_name = "Goal Type"
    option_unique_characters = 0
    option_total_wins = 1
    option_spirits = 2
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


class GameMode(Choice):
    """Which game mode locations are included. Only checks for the selected mode exist in the seed."""
    display_name = "Game Mode"
    option_standard = 0
    option_street_brawl = 1
    default = 0


@dataclass
class DeadlockOptions(PerGameCommonOptions):
    goal_type: GoalType
    unique_characters_to_win: UniqueCharactersToWin
    total_wins_to_win: TotalWinsToWin
    spirits_to_win: SpiritsToWin
    game_mode: GameMode
