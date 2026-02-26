from __future__ import annotations

from dataclasses import dataclass
from Options import Choice, Range, PerGameCommonOptions


class GoalType(Choice):
    """How game completion is determined.

    - **Unique Characters:** Win with N different characters.
    - **Total Wins:** Win N matches total.
    """
    display_name = "Goal Type"
    option_unique_characters = 0
    option_total_wins = 1
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


@dataclass
class DeadlockOptions(PerGameCommonOptions):
    goal_type: GoalType
    unique_characters_to_win: UniqueCharactersToWin
    total_wins_to_win: TotalWinsToWin
