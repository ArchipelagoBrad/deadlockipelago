from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
import ssl
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass, asdict
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Optional, Any

from CommonClient import CommonContext, gui_enabled, server_loop, console_loop, ClientCommandProcessor

try:
    from Utils import async_start
except Exception:
    async_start = None
try:
    from NetUtils import ClientStatus
except Exception:
    ClientStatus = None  # type: ignore[misc, assignment]

logger = logging.getLogger("Client")

_api_tls_context: ssl.SSLContext | None = None


def _deadlock_api_tls_context() -> ssl.SSLContext:
    """
    TLS context for https://api.deadlock-api.com requests.
    Prefer certifi's Mozilla CA bundle so native Linux/AppImage Python builds
    that lack a system CA path still verify public API certificates.
    """
    global _api_tls_context
    if _api_tls_context is not None:
        return _api_tls_context
    try:
        import certifi

        _api_tls_context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        _api_tls_context = ssl.create_default_context()
    return _api_tls_context


# Full SteamID3 e.g. [U:1:123456789], or digits-only e.g. 123456789
STEAMID3_FULL_RE = re.compile(r"^\[U:1:(\d+)\]$")
STEAMID3_DIGITS_RE = re.compile(r"^\d+$")


def _steamid3_to_digits(value: str) -> Optional[str]:
    """Accept [U:1:123456789] or 123456789; return only the digits or None if invalid."""
    value = value.strip()
    full = STEAMID3_FULL_RE.match(value)
    if full:
        return full.group(1)
    if STEAMID3_DIGITS_RE.match(value):
        return value
    return None


@dataclass
class DeadlockSave:
    # Per-seed metadata (seed_name will be filled once connected)
    seed_name: str = "unconnected"
    start_date_local: str = ""  # ISO8601 with local offset, set once at creation

    # Player config: stored as digits only (e.g. "123456789")
    steamid3: Optional[str] = None

    # Persistent totals
    games_submitted: int = 0
    kills_total: int = 0
    assists_total: int = 0
    souls_total: int = 0
    wins_total: int = 0
    neutral_camps_total: int = 0
    sinners_jackpots_total: int = 0
    key_player_matches_total: int = 0   # mvp_rank in (1, 2, 3)
    mvp_matches_total: int = 0         # mvp_rank == 1
    boss_damage_total: int = 0         # from stats[-1].boss_damage per match
    player_damage_total: int = 0       # from stats[-1].player_damage per match
    denies_total: int = 0
    last_hits_total: int = 0

    # Street Brawl (game_mode 4) – only used when seed is Street Brawl
    street_brawl_round_wins_total: int = 0
    street_brawl_round_win_under_90s: bool = False
    street_brawl_round_win_under_120s: bool = False
    street_brawl_match_3_0: bool = False
    street_brawl_match_under_7m: bool = False
    street_brawl_match_under_10m: bool = False
    street_brawl_win_no_deaths: bool = False
    street_brawl_win_10_plus_kills: bool = False

    # Unique heroes we've won with (authoritative for goal; not derived from server state)
    unique_heroes_won: list[str] = None

    # Anti-duplicate
    submitted_match_ids: list[str] = None

    def __post_init__(self) -> None:
        if self.submitted_match_ids is None:
            self.submitted_match_ids = []
        if not isinstance(self.unique_heroes_won, list):
            self.unique_heroes_won = []
        if not self.start_date_local:
            self.start_date_local = datetime.now().astimezone().replace(microsecond=0).isoformat()
        # Normalise steamid3 to digits-only (migrate old saves that stored full [U:1:...])
        if self.steamid3:
            digits = _steamid3_to_digits(self.steamid3)
            self.steamid3 = digits if digits else self.steamid3


def _get_save_dir() -> Path:
    try:
        from Utils import user_path  # type: ignore
        return Path(user_path("saves", "deadlock"))
    except Exception:
        return Path(".") / "deadlock_saves"


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:120]


def _accolade_value(player: dict, accolade_id: int) -> int:
    """Return accolade_stat_value for the given accolade_id from player's accolades, or 0."""
    for a in player.get("accolades") or []:
        if isinstance(a, dict) and a.get("accolade_id") == accolade_id:
            v = a.get("accolade_stat_value")
            return int(v) if v is not None else 0
    return 0


# Goal type values (must match options.GoalType)
GOAL_UNIQUE_CHARACTERS = 0
GOAL_TOTAL_WINS = 1
GOAL_SPIRITS = 2
GOAL_WIN_WITH_CHARACTER = 3

# MacGuffin item name (must match items.FILLER_ITEM_NAME)
SPIRITS_ITEM_NAME = "Spirits"

# Game mode from API (match_info.game_mode)
GAME_MODE_STREET_BRAWL = 4


def _get_goal_options(slot_data: dict) -> tuple[int, int, int, int, int, str]:
    """Return (goal_type, unique_characters_to_win, total_wins_to_win, spirits_to_win, spirits_to_unlock_final, final_character) from slot_data."""
    if not isinstance(slot_data, dict):
        slot_data = {}
    raw_goal = slot_data.get("goal_type", GOAL_UNIQUE_CHARACTERS)
    if raw_goal in (1, "1", "total_wins"):
        goal_type = GOAL_TOTAL_WINS
    elif raw_goal in (2, "2", "spirits"):
        goal_type = GOAL_SPIRITS
    elif raw_goal in (3, "3", "win_with_character"):
        goal_type = GOAL_WIN_WITH_CHARACTER
    else:
        goal_type = GOAL_UNIQUE_CHARACTERS
    raw_unique = slot_data.get("unique_characters_to_win", 10)
    raw_total = slot_data.get("total_wins_to_win", 25)
    raw_spirits = slot_data.get("spirits_to_win", 10)
    raw_spirits_unlock = slot_data.get("spirits_to_unlock_final", 10)
    final_character = str(slot_data.get("final_character", "") or "").strip()
    try:
        unique = int(raw_unique)
    except (TypeError, ValueError):
        unique = 10
    try:
        total_wins = int(raw_total)
    except (TypeError, ValueError):
        total_wins = 25
    try:
        spirits = int(raw_spirits)
    except (TypeError, ValueError):
        spirits = 10
    try:
        spirits_unlock = int(raw_spirits_unlock)
    except (TypeError, ValueError):
        spirits_unlock = 10
    unique = max(1, min(38, unique))
    total_wins = max(1, min(100, total_wins))
    max_spirits = 143 if slot_data.get("game_mode", 0) == 1 else 162
    spirits = max(1, min(max_spirits, spirits))
    spirits_unlock = max(1, min(max_spirits, spirits_unlock))
    return (goal_type, unique, total_wins, spirits, spirits_unlock, final_character)


def _load_hero_id_to_name() -> dict[int, str]:
    """Load hero_id -> hero name from deadlock/data/heroes.csv (works with apworld zip)."""
    out: dict[int, str] = {}
    try:
        with resources.files(__package__).joinpath("data/heroes.csv").open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                out[int(row["id"])] = row["name"].strip()
    except Exception as e:
        logger.warning("Could not load heroes.csv: %s", e)
    return out


def _count_spirits_received(ctx: "DeadlockContext") -> int:
    """Return how many Spirits (MacGuffin) items the player has received."""
    try:
        game_items = ctx.item_names[ctx.game]
    except (KeyError, TypeError, AttributeError):
        game_items = {}
    count = 0
    for net_item in getattr(ctx, "items_received", []):
        item_id = getattr(net_item, "item", None)
        if item_id is None:
            continue
        if game_items.get(item_id) == SPIRITS_ITEM_NAME:
            count += 1
    return count


async def _warn_if_no_heroes_after_delay(ctx: "DeadlockContext", delay_seconds: float = 3.0) -> None:
    """Run after Connected: wait for initial item sync, then warn once if the player has no Unlock heroes."""
    await asyncio.sleep(delay_seconds)
    heroes = ctx._unlocked_heroes_from_items()
    if not heroes and not getattr(ctx, "_warned_no_heroes", False):
        ctx.output(
            "You have no characters unlocked. If you did not set starting heroes, create your YAML with the "
            "Player Options generator (https://archipelagobrad.github.io/deadlockipelago/index.html) and "
            "regenerate the multiworld so you receive Unlock items."
        )
        ctx._warned_no_heroes = True


async def _check_goal_and_send_if_met(
    ctx: "DeadlockContext",
    location_name_to_id: dict[str, int] | None = None,
    missing: set[int] | None = None,
    wins_after: int | None = None,
    hero_name_this_win: str | None = None,
) -> None:
    """If the player has met their win condition, send the Goal location check and status."""
    if location_name_to_id is None:
        try:
            game_locations = ctx.location_names[ctx.game]
        except (KeyError, TypeError):
            game_locations = {}
        location_name_to_id = {name: loc_id for loc_id, name in game_locations.items()}
    if missing is None:
        missing = getattr(ctx, "missing_locations", set())
    if wins_after is None:
        wins_after = ctx.save.wins_total
    slot_data = getattr(ctx, "slot_data", None) or {}
    goal_type, unique_req, total_wins_req, spirits_req, spirits_unlock_req, final_character = _get_goal_options(slot_data)
    goal_met = False
    if goal_type == GOAL_UNIQUE_CHARACTERS and len(ctx.save.unique_heroes_won) >= unique_req:
        goal_met = True
    elif goal_type == GOAL_TOTAL_WINS and wins_after >= total_wins_req:
        goal_met = True
    elif goal_type == GOAL_SPIRITS:
        if _count_spirits_received(ctx) >= spirits_req:
            goal_met = True
    elif goal_type == GOAL_WIN_WITH_CHARACTER and final_character and hero_name_this_win is not None:
        if _count_spirits_received(ctx) >= spirits_unlock_req and hero_name_this_win == final_character:
            goal_met = True
    if goal_met and ClientStatus is not None:
        goal_loc_id = location_name_to_id.get("Goal")
        if goal_loc_id is not None and goal_loc_id in missing:
            await ctx.check_locations([goal_loc_id])
            ctx.output("Goal completed! You have met the win condition.")
            ctx.finished_game = True
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])


async def _submit_match_impl(ctx: "DeadlockContext", match_id: str) -> None:
    """Fetch match metadata, compute earned locations (hero wins, matches, wins, Soul Urn, kills, assists, souls), send checks, update save."""
    ctx.ensure_seed_save_loaded()
    if match_id in ctx.save.submitted_match_ids:
        ctx.output(f"Match {match_id} was already submitted.")
        return
    if not ctx.save.steamid3:
        ctx.output("SteamID3 not set. Use /set_player_id first.")
        return

    api_url = f"https://api.deadlock-api.com/v1/matches/{match_id}/metadata"

    def _fetch() -> bytes:
        req = urllib.request.Request(api_url, headers={"User-Agent": "Archipelago-Deadlock-Client/1.0"})
        ctx = _deadlock_api_tls_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return resp.read()

    try:
        raw = await asyncio.to_thread(_fetch)
    except HTTPError as e:
        code = e.code
        if code == 404:
            ctx.output("Match not found (404). Double-check that the match ID is correct, or wait 5 minutes to allow the API time to ingest the match.")
        elif code == 429:
            ctx.output("API rate limit reached (429). Please try again in an hour — the API allows 5 requests per hour.")
        elif code == 503:
            ctx.output("API temporarily unavailable (503). Please wait 5 minutes and try again.")
        else:
            ctx.output(f"Failed to fetch match data: HTTP Error {code}: {e.reason}")
        return
    except Exception as e:
        ctx.output(f"Failed to fetch match data: {e}")
        return

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        ctx.output(f"Invalid JSON from API: {e}")
        return

    match_info = data.get("match_info")
    if not match_info or not isinstance(match_info, dict):
        ctx.output("API response missing match_info.")
        return

    # Reject matches that started before this save (anti-scumming)
    match_start_time = match_info.get("start_time")
    if match_start_time is None:
        ctx.output("Match start time not available from API; cannot verify the match was played after this save started.")
        return
    try:
        match_start_ts = int(match_start_time)
    except (TypeError, ValueError):
        ctx.output("Invalid match start_time from API.")
        return
    if ctx.save.start_date_local:
        try:
            save_start_dt = datetime.fromisoformat(ctx.save.start_date_local)
            save_start_ts = save_start_dt.timestamp()
        except (TypeError, ValueError):
            save_start_ts = 0  # allow if save date unparseable (e.g. old save)
        else:
            if match_start_ts < save_start_ts:
                ctx.output(
                    "Match was started before this Archipelago save. Only matches played after you started this seed can be submitted."
                )
                return # disabled for testing

    players = match_info.get("players") or []
    winning_team = match_info.get("winning_team")
    if winning_team is None:
        ctx.output("API response missing winning_team.")
        return

    steamid3 = ctx.save.steamid3
    player = None
    for p in players:
        if not isinstance(p, dict):
            continue
        aid = p.get("account_id")
        if aid is not None and str(aid) == steamid3:
            player = p
            break

    if not player:
        ctx.output(f"Player not found in match (SteamID3 {steamid3}). Wrong match or ID.")
        return

    player_team = player.get("team")
    player_won = player_team is not None and player_team == winning_team
    match_game_mode = match_info.get("game_mode")
    try:
        match_game_mode = int(match_game_mode) if match_game_mode is not None else None
    except (TypeError, ValueError):
        match_game_mode = None
    hero_id = player.get("hero_id")
    hero_id_to_name = _load_hero_id_to_name()
    hero_name = hero_id_to_name.get(hero_id) if hero_id is not None else None

    # Anti-scumming: require the player to have unlocked this hero (via items or, for Win with Character goal, final character once spirits >= X)
    if hero_name is None:
        ctx.output("Cannot submit this match: the hero you played could not be identified (hero_id not in game data).")
        return
    slot_data = getattr(ctx, "slot_data", None) or {}
    unlocked_heroes = set(ctx._unlocked_heroes_from_items())
    goal_type, _, _, _, spirits_unlock_req, final_character = _get_goal_options(slot_data)
    if goal_type == GOAL_WIN_WITH_CHARACTER and final_character and _count_spirits_received(ctx) >= spirits_unlock_req:
        unlocked_heroes.add(final_character)
    if hero_name not in unlocked_heroes:
        ctx.output("You cannot submit this match: you have not unlocked this character yet.")
        return # disabled for testing

    # Match stats (for this match only)
    player_kills = int(player.get("kills") or 0)
    player_assists = int(player.get("assists") or 0)
    net_worth = int(player.get("net_worth") or 0)
    accolade_urn = _accolade_value(player, 13)  # returned_idol / Soul Urn
    accolade_neutrals = _accolade_value(player, 7)   # neutral_last_hits
    accolade_jackpots = _accolade_value(player, 14)  # sinners_sacrifice_jackpot

    # MVP / key player (mvp_rank: 1 = MVP, 2 or 3 = key player)
    mvp_rank_raw = player.get("mvp_rank")
    mvp_rank = int(mvp_rank_raw) if mvp_rank_raw is not None else None
    is_key_player = mvp_rank is not None and mvp_rank in (1, 2, 3)
    is_mvp = mvp_rank == 1

    # Damage and stats from final snapshot (stats[-1]); top-level denies/last_hits are match totals
    stats_list = player.get("stats") or []
    last_stat = stats_list[-1] if stats_list else {}
    match_boss_damage = int(last_stat.get("boss_damage") or 0)
    match_player_damage = int(last_stat.get("player_damage") or 0)
    match_denies = int(player.get("denies") or 0)
    match_last_hits = int(player.get("last_hits") or 0)

    # Totals after this match is counted
    games_after = ctx.save.games_submitted + 1
    wins_after = ctx.save.wins_total + (1 if player_won else 0)
    kills_after = ctx.save.kills_total + player_kills
    assists_after = ctx.save.assists_total + player_assists
    souls_after = ctx.save.souls_total + net_worth
    neutral_camps_after = ctx.save.neutral_camps_total + accolade_neutrals
    sinners_jackpots_after = ctx.save.sinners_jackpots_total + accolade_jackpots
    key_player_after = ctx.save.key_player_matches_total + (1 if is_key_player else 0)
    mvp_after = ctx.save.mvp_matches_total + (1 if is_mvp else 0)
    boss_damage_after = ctx.save.boss_damage_total + match_boss_damage
    player_damage_after = ctx.save.player_damage_total + match_player_damage
    denies_after = ctx.save.denies_total + match_denies
    last_hits_after = ctx.save.last_hits_total + match_last_hits

    earned_location_names: list[str] = []
    try:
        game_locations = ctx.location_names[ctx.game]
    except (KeyError, TypeError):
        game_locations = {}
    if not game_locations:
        ctx.output("No location names loaded (connect to server first).")
        return

    location_name_to_id = {name: loc_id for loc_id, name in game_locations.items()}
    checked = ctx.checked_locations

    def _add_if_earned(loc_name: str) -> None:
        loc_id = location_name_to_id.get(loc_name)
        if loc_id is not None and loc_id not in checked:
            earned_location_names.append(loc_name)

    # Hero wins (all three rewards)
    if player_won and hero_name:
        for n in (1, 2, 3):
            _add_if_earned(f"Win a game as {hero_name} (Reward {n}/3)")

    # Matches played: 5, 10, 20, 50
    for threshold in (5, 10, 20, 50):
        if games_after >= threshold:
            _add_if_earned(f"Complete {threshold} matches")

    # Wins: Win 1 match; Win 5/10/15/20/25 matches (Reward 1/5 .. 5/5)
    if wins_after >= 1:
        _add_if_earned("Win 1 match")
    for win_threshold in (5, 10, 15, 20, 25):
        if wins_after >= win_threshold:
            for k in range(1, 6):
                _add_if_earned(f"Win {win_threshold} matches (Reward {k}/5)")

    # Standard-only: Soul Urn, neutrals, Sinner's (disabled in Street Brawl seeds)
    if match_game_mode != GAME_MODE_STREET_BRAWL:
        if accolade_urn >= 1:
            _add_if_earned("Deliver the Soul Urn")
        for threshold in (1, 5, 10, 25, 50, 100):
            if neutral_camps_after >= threshold:
                _add_if_earned(f"Kill {threshold} neutral camp" + ("s" if threshold != 1 else ""))
        for threshold in (25, 50, 100, 250):
            if sinners_jackpots_after >= threshold:
                _add_if_earned(f"Sinner's Sacrifice jackpot ({threshold})")

    # Kills: 1, 10, 25, 50, 100, 250
    for threshold in (1, 10, 25, 50, 100, 250):
        if kills_after >= threshold:
            _add_if_earned(f"Kill {threshold} enemy hero" + ("es" if threshold != 1 else ""))

    # Assists: 1, 10, 25, 50, 100, 250
    for threshold in (1, 10, 25, 50, 100, 250):
        if assists_after >= threshold:
            _add_if_earned(f"Get {threshold} assist" + ("s" if threshold != 1 else ""))

    # Standard-only: souls (disabled in Street Brawl seeds)
    if match_game_mode != GAME_MODE_STREET_BRAWL:
        soul_thresholds = [(10_000, "10k"), (50_000, "50k"), (100_000, "100k"), (250_000, "250k"), (500_000, "500k"), (1_000_000, "1m")]
        for value, label in soul_thresholds:
            if souls_after >= value:
                _add_if_earned(f"Earn {label} souls")

    # Key player (mvp_rank 1, 2, or 3): 5, 10, 25 matches
    for threshold in (5, 10, 25):
        if key_player_after >= threshold:
            _add_if_earned(f"Be a Key Player in {threshold} Matches")

    # MVP (mvp_rank 1): 1, 3, 5 matches
    for threshold in (1, 3, 5):
        if mvp_after >= threshold:
            _add_if_earned(f"Be the MVP in {threshold} Match" + ("es" if threshold != 1 else ""))

    # Standard-only: boss damage (disabled in Street Brawl seeds)
    if match_game_mode != GAME_MODE_STREET_BRAWL:
        boss_cumul = [(10_000, "10k"), (25_000, "25k"), (50_000, "50k"), (100_000, "100k")]
        for value, label in boss_cumul:
            if boss_damage_after >= value:
                _add_if_earned(f"Deal {label} Boss Damage")
        if match_boss_damage >= 5_000:
            _add_if_earned("Deal 5k Boss Damage in a Match")
        if match_boss_damage >= 10_000:
            _add_if_earned("Deal 10k Boss Damage in a Match")

    # Player damage (cumulative): 100k, 250k, 500k, 1m
    player_cumul = [(100_000, "100k"), (250_000, "250k"), (500_000, "500k"), (1_000_000, "1m")]
    for value, label in player_cumul:
        if player_damage_after >= value:
            _add_if_earned(f"Deal {label} Player Damage")

    # Player damage in a single match: 10k, 20k, 30k
    for threshold, label in [(10_000, "10k"), (20_000, "20k"), (30_000, "30k")]:
        if match_player_damage >= threshold:
            _add_if_earned(f"Deal {label} Player Damage in a Match")

    # Standard-only: denies, last hits (disabled in Street Brawl seeds)
    if match_game_mode != GAME_MODE_STREET_BRAWL:
        for threshold in (10, 25, 50):
            if denies_after >= threshold:
                _add_if_earned(f"Get {threshold} Denies")
        last_hits_cumul = [(250, "250"), (500, "500"), (1_000, "1k"), (2_000, "2k")]
        for value, label in last_hits_cumul:
            if last_hits_after >= value:
                _add_if_earned(f"Get {label} Last Hits")

    # Street Brawl-only checks (match must be game_mode 4)
    if match_game_mode == GAME_MODE_STREET_BRAWL:
        street_brawl_rounds = data.get("street_brawl_rounds") or []
        rounds_won_this_match = sum(1 for r in street_brawl_rounds if isinstance(r, dict) and r.get("winning_team") == player_team)
        round_win_under_90 = False
        round_win_under_120 = False
        for r in street_brawl_rounds:
            if not isinstance(r, dict) or r.get("winning_team") != player_team:
                continue
            dur = r.get("round_duration_s")
            try:
                dur = int(dur) if dur is not None else 999
            except (TypeError, ValueError):
                dur = 999
            if dur < 90:
                round_win_under_90 = True
            if dur < 120:
                round_win_under_120 = True
        match_duration_s = match_info.get("duration_s")
        try:
            match_duration_s = int(match_duration_s) if match_duration_s is not None else 99999
        except (TypeError, ValueError):
            match_duration_s = 99999
        team_0_rounds = sum(1 for r in street_brawl_rounds if isinstance(r, dict) and r.get("winning_team") == 0)
        team_1_rounds = sum(1 for r in street_brawl_rounds if isinstance(r, dict) and r.get("winning_team") == 1)
        match_3_0 = (player_team == 0 and team_0_rounds == 3 and team_1_rounds == 0) or (player_team == 1 and team_1_rounds == 3 and team_0_rounds == 0)
        no_deaths = len(player.get("death_details") or []) == 0
        ten_plus_kills = (player_kills or 0) >= 10

        sb_round_wins_after = ctx.save.street_brawl_round_wins_total + rounds_won_this_match
        for threshold in (5, 10, 25, 50):
            if sb_round_wins_after >= threshold:
                _add_if_earned(f"Win {threshold} Street Brawl rounds")
        if round_win_under_90 or ctx.save.street_brawl_round_win_under_90s:
            _add_if_earned("Win a Street Brawl round in under 1m 30s")
        if round_win_under_120 or ctx.save.street_brawl_round_win_under_120s:
            _add_if_earned("Win a Street Brawl round in under 2m")
        if match_3_0 or ctx.save.street_brawl_match_3_0:
            _add_if_earned("Win a Street Brawl match 3-0")
        if (match_duration_s < 420 and player_won) or ctx.save.street_brawl_match_under_7m:
            _add_if_earned("Win a Street Brawl match in under 7m")
        if (match_duration_s < 600 and player_won) or ctx.save.street_brawl_match_under_10m:
            _add_if_earned("Win a Street Brawl match in under 10m")
        if (player_won and no_deaths) or ctx.save.street_brawl_win_no_deaths:
            _add_if_earned("Win a Street Brawl without dying")
        if (player_won and ten_plus_kills) or ctx.save.street_brawl_win_10_plus_kills:
            _add_if_earned("Win a Street Brawl with 10+ kills")

        # Persist Street Brawl stats
        ctx.save.street_brawl_round_wins_total += rounds_won_this_match
        if round_win_under_90:
            ctx.save.street_brawl_round_win_under_90s = True
        if round_win_under_120:
            ctx.save.street_brawl_round_win_under_120s = True
        if match_3_0:
            ctx.save.street_brawl_match_3_0 = True
        if player_won and match_duration_s < 420:
            ctx.save.street_brawl_match_under_7m = True
        if player_won and match_duration_s < 600:
            ctx.save.street_brawl_match_under_10m = True
        if player_won and no_deaths:
            ctx.save.street_brawl_win_no_deaths = True
        if player_won and ten_plus_kills:
            ctx.save.street_brawl_win_10_plus_kills = True

    # location_name_to_id already built above from game_locations
    missing = ctx.missing_locations
    to_send = []
    for name in earned_location_names:
        loc_id = location_name_to_id.get(name)
        if loc_id is not None and loc_id in missing:
            to_send.append(loc_id)

    if to_send:
        await ctx.check_locations(to_send)
        sent_names = [n for n, lid in location_name_to_id.items() if lid in to_send]
        ctx.output(f"Submitted {len(to_send)} location check(s): {', '.join(sent_names)}")
    elif earned_location_names:
        ctx.output("No new checks to send (locations already checked).")
    else:
        if not player_won:
            ctx.output("Match submitted (loss — no hero-win check).")
        elif not hero_name:
            ctx.output(f"Match submitted (hero_id {hero_id} not in heroes list — no check).")
        else:
            ctx.output("Match submitted (all three hero-win rewards already earned for this hero).")

    ctx.save.submitted_match_ids.append(match_id)
    ctx.save.games_submitted += 1
    ctx.save.kills_total += player_kills
    ctx.save.assists_total += player_assists
    ctx.save.souls_total += net_worth
    ctx.save.neutral_camps_total += accolade_neutrals
    ctx.save.sinners_jackpots_total += accolade_jackpots
    if is_key_player:
        ctx.save.key_player_matches_total += 1
    if is_mvp:
        ctx.save.mvp_matches_total += 1
    ctx.save.boss_damage_total += match_boss_damage
    ctx.save.player_damage_total += match_player_damage
    ctx.save.denies_total += match_denies
    ctx.save.last_hits_total += match_last_hits
    if player_won:
        ctx.save.wins_total += 1
        if hero_name and hero_name not in ctx.save.unique_heroes_won:
            ctx.save.unique_heroes_won.append(hero_name)
    ctx.save_save()

    # Win condition: check goal and send Goal location if met (use save-backed stats only)
    await _check_goal_and_send_if_met(
        ctx, location_name_to_id, missing, wins_after,
        hero_name_this_win=hero_name if player_won else None,
    )


class DeadlockCommandProcessor(ClientCommandProcessor):
    """Deadlock client commands."""

    def _cmd_heroes(self) -> None:
        """List heroes unlocked via received 'Unlock <Hero>' items (requires connection)."""
        self.ctx.cmd_heroes()

    def _cmd_goal(self) -> None:
        """Show your goal and how far you are from completing it."""
        self.ctx.cmd_goal()

    def _cmd_set_player_id(self, steamid3: str = "") -> None:
        """Set your SteamID3. Usage: /set_player_id [U:1:123456789] or /set_player_id 123456789"""
        self.ctx.cmd_set_player_id([steamid3] if steamid3 else [])

    def _cmd_steamid3(self, steamid3: str = "") -> None:
        """Alias for /set_player_id."""
        self._cmd_set_player_id(steamid3)

    def _cmd_stats(self) -> None:
        """Show games, kills, assists and souls totals for this save."""
        self.ctx.cmd_stats()

    def _cmd_statistics(self) -> None:
        """Alias for /stats."""
        self._cmd_stats()

    def _cmd_save_path(self) -> None:
        """Show the active save file path and seed metadata."""
        self.ctx.cmd_save_path()

    def _cmd_submit_match(self, match_id: str = "") -> None:
        """Submit a match ID. Usage: /submit_match <match_id>"""
        self.ctx.cmd_submit_match([match_id] if match_id else [])

    def _cmd_submit(self, match_id: str = "") -> None:
        """Alias for /submit_match."""
        self._cmd_submit_match(match_id)

    def _cmd_s(self, match_id: str = "") -> None:
        """Alias for /submit_match."""
        self._cmd_submit_match(match_id)


class DeadlockContext(CommonContext):
    game = "Deadlock"

    def __init__(self, server_address: Optional[str] = None, password: Optional[str] = None) -> None:
        super().__init__(server_address, password)

        # IMPORTANT: KVUI expects a callable/class here (0.6.6)
        self.command_processor = DeadlockCommandProcessor

        self.items_handling = 0b111

        # Seed name arrives via RoomInfo. Start empty so CommonClient's RoomInfo check
        # (ctx.seed_name != args["seed_name"]) is skipped on first connect; we then
        # set it from RoomInfo. Use "unconnected" only for save paths when not connected.
        self.seed_name: str = ""

        self.save: DeadlockSave = DeadlockSave(seed_name=self.seed_name)
        self._save_path: Optional[Path] = None
        self._save_loaded_for_seed: bool = False

        # load offline save immediately so /stats and /set_player_id work before connect
        self.ensure_seed_save_loaded()

    # ---------- output ----------
    def output(self, text: str) -> None:
    # This shows in the GUI log pane (because of logging_pairs = [("Client","Archipelago")])
        try:
            logger.info(text)
        except Exception:
            # ultra-safe fallback
            print(text)

    # ---------- connection state ----------
    def is_connected(self) -> bool:
        # CommonContext sets .server when websocket is connected; slot is set after auth.
        return bool(getattr(self, "server", None)) and bool(getattr(self, "slot", None))

    async def server_auth(self, password_requested: bool = False) -> None:
        """After RoomInfo, get slot name (if needed) and send Connect packet so the server joins us to the room."""
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect(game="Deadlock")

    # ---------- packets ----------
    def on_package(self, cmd: str, args: dict[str, Any]) -> None:
        if cmd == "RoomInfo":
            new_seed = args.get("seed_name") or "unknown_seed"
            if isinstance(new_seed, str) and new_seed:
                if new_seed != self.seed_name:
                    # When seed changes, rotate save
                    self.seed_name = new_seed
                    self._save_loaded_for_seed = False
                    self._warned_no_heroes = False
                    self.ensure_seed_save_loaded(migrate_from_unconnected=True)
        elif cmd == "Connected":
            # Store slot_data so we can read goal options (goal_type, unique_characters_to_win, total_wins_to_win, spirits_to_win)
            setattr(self, "slot_data", args.get("slot_data") or {})
            super().on_package(cmd, args)
            # Defer the "no heroes" check so initial ReceivedItems (e.g. start_inventory) have time to arrive
            if async_start:
                async_start(_warn_if_no_heroes_after_delay(self), name="warn_no_heroes")
            return
        elif cmd == "ReceivedItems":
            # Spirits (MacGuffin) goal can be met by receiving items; check after each batch
            if async_start:
                async_start(_check_goal_and_send_if_met(self), name="check_goal")

        super().on_package(cmd, args)

    # ---------- persistence ----------
    def _compute_save_path(self, seed_name: Optional[str] = None) -> Path:
        """Save path uses only seed and slot so it stays stable when server host/port or team changes."""
        slot = self.auth or "no_slot"
        seed = seed_name or self.seed_name or "unconnected"
        base = f"deadlock__{_safe_filename(seed)}__{_safe_filename(slot)}"
        return _get_save_dir() / f"{base}.json"

    def _compute_legacy_save_path(self, seed_name: Optional[str] = None) -> Path:
        """Old path (server, team, slot, seed) for one-time migration only."""
        server = self.server_address or "no_server"
        slot = self.auth or "no_slot"
        team = str(getattr(self, "team", "0"))
        seed = seed_name or self.seed_name or "unconnected"
        base = f"deadlock__{server}__{team}__{slot}__{seed}"
        return _get_save_dir() / f"{_safe_filename(base)}.json"

    def ensure_seed_save_loaded(self, migrate_from_unconnected: bool = False) -> None:
        if self._save_loaded_for_seed:
            return

        path = self._compute_save_path()
        self._save_path = path

        try:
            # If we're connecting for the first time and have an "unconnected" save, migrate it
            if migrate_from_unconnected and not path.exists():
                unconnected_path = self._compute_save_path(seed_name="unconnected")
                if unconnected_path.exists():
                    data = json.loads(unconnected_path.read_text(encoding="utf-8"))
                    migrated = DeadlockSave(**data)
                    migrated.seed_name = self.seed_name
                    self.save = migrated
                    self._save_loaded_for_seed = True
                    self.save_save()
                    self.output(f"Migrated Deadlock save to seed '{self.seed_name}': {path.name}")
                    return

            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                self.save = DeadlockSave(**data)
                self.save.seed_name = self.seed_name
                self._save_loaded_for_seed = True
                return

            # One-time migration from old path (server__team__slot__seed) if it exists
            legacy_path = self._compute_legacy_save_path()
            if legacy_path.exists():
                data = json.loads(legacy_path.read_text(encoding="utf-8"))
                self.save = DeadlockSave(**data)
                self.save.seed_name = self.seed_name
                self._save_loaded_for_seed = True
                self.save_save()
                self.output(f"Migrated Deadlock save to new path (seed+slot): {path.name}")
                return

            # Create new
            self.save = DeadlockSave(seed_name=self.seed_name)
            self._save_loaded_for_seed = True
            self.save_save()
        except Exception as e:
            self.output(f"Failed to load/create save ({path}): {e}")
            self._save_loaded_for_seed = True

    def save_save(self) -> None:
        if self._save_path is None:
            self._save_path = self._compute_save_path()
        self.save.seed_name = self.seed_name or self.save.seed_name or "unconnected"

        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_path.write_text(json.dumps(asdict(self.save), indent=2), encoding="utf-8")
        except Exception as e:
            self.output(f"Failed to write save ({self._save_path}): {e}")

    # ---------- GUI ----------
    def run_gui(self) -> None:
        from kvui import GameManager

        class DeadlockManager(GameManager):
            logging_pairs = [("Client", "Archipelago")]

        self.ui = DeadlockManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    # ---------- helpers ----------
    def _unlocked_heroes_from_items(self) -> list[str]:
        """Heroes unlocked by receiving 'Unlock <Hero>' items. Uses only items_received (items we have been given)."""
        prefix = "Unlock "
        heroes: set[str] = set()
        try:
            game_items = self.item_names[self.game]
        except (KeyError, TypeError):
            game_items = {}

        for net_item in getattr(self, "items_received", []):
            item_id = getattr(net_item, "item", None)
            if item_id is None:
                continue
            name = game_items.get(item_id, "")
            if name.startswith(prefix):
                heroes.add(name[len(prefix):].strip())

        return sorted(heroes, key=str.lower)

    # ---------- commands ----------
    def cmd_heroes(self) -> None:
        if not self.is_connected():
            self.output("Not connected to an Archipelago server. Connect first, then use /heroes.")
            return

        self.ensure_seed_save_loaded()
        heroes = list(self._unlocked_heroes_from_items())
        slot_data = getattr(self, "slot_data", None) or {}
        goal_type, _, _, _, spirits_unlock_req, final_character = _get_goal_options(slot_data)
        if goal_type == GOAL_WIN_WITH_CHARACTER and final_character and _count_spirits_received(self) >= spirits_unlock_req:
            if final_character not in heroes:
                heroes.append(final_character)
                heroes.sort(key=str.lower)
        if not heroes:
            self.output("Unlocked heroes: (none yet)")
            self.output("Tip: you'll see heroes here after receiving 'Unlock <Hero>' items.")
            return

        won_with = set(self.save.unique_heroes_won)
        parts = [f"{h} *" if h in won_with else h for h in heroes]
        self.output(f"Unlocked heroes ({len(heroes)}): " + ", ".join(parts))
        if won_with:
            self.output("(* = already have a win with this hero)")
        if goal_type == GOAL_WIN_WITH_CHARACTER and final_character and final_character in heroes:
            self.output(f"(Final goal character: win with {final_character} to complete.)")

    def cmd_goal(self) -> None:
        """Show current goal and progress toward it."""
        if not self.is_connected():
            self.output("Not connected. Connect to an Archipelago server to see your goal.")
            return
        self.ensure_seed_save_loaded()
        slot_data = getattr(self, "slot_data", None) or {}
        goal_type, unique_req, total_wins_req, spirits_req, spirits_unlock_req, final_character = _get_goal_options(slot_data)

        if goal_type == GOAL_UNIQUE_CHARACTERS:
            current = len(self.save.unique_heroes_won)
            self.output(f"Goal: Win with {unique_req} unique character(s).")
            self.output(f"Progress: {current} / {unique_req} unique character(s) won with.")
        elif goal_type == GOAL_TOTAL_WINS:
            current = self.save.wins_total
            self.output(f"Goal: Win {total_wins_req} match(es).")
            self.output(f"Progress: {current} / {total_wins_req} win(s).")
        elif goal_type == GOAL_WIN_WITH_CHARACTER and final_character:
            spirits_current = _count_spirits_received(self)
            self.output(f"Goal: Collect {spirits_unlock_req} Spirits to unlock your final character, then win one match with them.")
            self.output(f"Win with: {final_character}")
            self.output(f"Progress: {spirits_current} / {spirits_unlock_req} Spirits. Then win one match with {final_character}.")
        else:
            current = _count_spirits_received(self)
            self.output(f"Goal: Collect {spirits_req} Spirits (MacGuffin).")
            self.output(f"Progress: {current} / {spirits_req} Spirits received.")

    def cmd_set_player_id(self, args: list[str]) -> None:
        self.ensure_seed_save_loaded()

        if not args:
            self.output("Usage: /set_player_id [U:1:123456789] or /set_player_id 123456789")
            return

        digits = _steamid3_to_digits(args[0])
        if digits is None:
            self.output(f"Invalid SteamID3 '{args[0].strip()}'. Use [U:1:123456789] or 123456789")
            return

        self.save.steamid3 = digits
        self.save_save()
        self.output(f"SteamID3 set to {digits} (saved locally).")

    def cmd_stats(self) -> None:
        self.ensure_seed_save_loaded()
        self.output(
            "Deadlock stats:\n"
            f"  Total games: {self.save.games_submitted}\n"
            f"  Wins: {self.save.wins_total}\n"
            f"  Total kills: {self.save.kills_total}\n"
            f"  Total assists: {self.save.assists_total}\n"
            f"  Total souls: {self.save.souls_total}\n"
            f"  Neutral camps: {self.save.neutral_camps_total}\n"
            f"  Sinner's Sacrifice jackpots: {self.save.sinners_jackpots_total}\n"
            f"  Key player matches: {self.save.key_player_matches_total}\n"
            f"  MVP matches: {self.save.mvp_matches_total}\n"
            f"  Boss damage: {self.save.boss_damage_total:,}\n"
            f"  Player damage: {self.save.player_damage_total:,}\n"
            f"  Denies: {self.save.denies_total}\n"
            f"  Last hits: {self.save.last_hits_total}\n"
            f"  Street Brawl round wins: {self.save.street_brawl_round_wins_total}\n"
        )

    def cmd_submit_match(self, args: list[str]) -> None:
        self.ensure_seed_save_loaded()

        if not args:
            self.output("Usage: /submit_match <match_id>  (aliases: /submit, /s)")
            return
        if not self.is_connected():
            self.output("Connect to an Archipelago server first.")
            return
        if not self.save.steamid3:
            self.output("SteamID3 not set. Use: /set_player_id [U:1:123456789] or /set_player_id 123456789")
            return

        match_id = args[0].strip()
        if async_start:
            async_start(_submit_match_impl(self, match_id), name="submit_match")
        else:
            asyncio.run(_submit_match_impl(self, match_id))

    def cmd_save_path(self) -> None:
        self.ensure_seed_save_loaded()
        self.output(f"Deadlock save path: {self._compute_save_path()}")
        self.output(f"Seed: {self.seed_name or 'unconnected'}")
        self.output(f"Start date (local): {self.save.start_date_local}")


async def _main() -> None:
    ctx = DeadlockContext()
    if gui_enabled:
        ctx.run_gui()
        # Run server_loop as a task so it can return when no address without exiting the app.
        # Main loop waits for exit_event (set when user closes window / uses /exit) then shuts down.
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        await ctx.exit_event.wait()
        await ctx.shutdown()
    else:
        console_loop(ctx)
        await server_loop(ctx)


def run_deadlock_client(*args: str) -> None:
    asyncio.run(_main())