<p align="center">
  <img src="./deadlock-portraits/deadlock_logo.png" alt="Deadlock Archipelago" width="600">
</p>

An [Archipelago](https://archipelago.gg/) world and client for **Deadlock** - a meta-progression randomizer where locations are earned by playing matches (hero wins, match milestones, accolades) and items unlock heroes you can use. Complete your goal (e.g. win with N unique characters, N total wins, collect N **Spirits**, or **Win with Character** – collect Spirits to unlock a chosen hero, then win one match with them) to finish the seed. Supports **Standard** and **Street Brawl** game modes with mode-specific checks, and an option to **exclude hard locations** for a lighter run.

---

## Contents

- [Requirements](#requirements)
- [Recommended: Deadlock API Ingest](#recommended-deadlock-api-ingest)
- [Quickstart Guide](#quickstart-guide)
- [Installation](#installation)
- [Game Options](#game-options)
- [Items & Locations](#items--locations)
- [Client Usage](#client-usage)
- [Documentation](#documentation)

---

## Requirements

- **Archipelago** - [Archipelago Launcher](https://github.com/ArchipelagoMW/Archipelago/releases) or a compatible multiworld host.
- **Deadlock** - the game (Steam).
- **Steam account** - your SteamID3 is used to identify you in match data when submitting games.
- **Python 3.10+** - only if you run the world or client from source (e.g. development or non-apworld install).
- **[Deadlock API Ingest](https://github.com/deadlock-api/deadlock-api-ingest)** *(strongly recommended)* - see below. Without it, match data may be missing when you run `/submit_match`, causing failures or long waits.

---

### Recommended: Deadlock API Ingest

The Archipelago client fetches match data from **api.deadlock-api.com**. That API only has data for matches that have been *submitted* to it. If nobody has submitted a match, the client’s `/submit_match <match_id>` request will fail (e.g. 404 or missing data).

**[Deadlock API Ingest](https://github.com/deadlock-api/deadlock-api-ingest)** is a small background tool that watches your Steam HTTP cache for Deadlock replay references and automatically sends match IDs (and salts) to the Deadlock API. That allows the API to fetch and process the match from Valve’s servers. Once a match is in the API, the Archipelago client can retrieve it reliably when you run `/submit_match`.

**Why I recommend it:**

- **Fewer failures** - Your own matches are ingested soon after you play, so they’re available when you submit. Without Ingest, you may have to wait a long time or rely on someone else ingesting the match.
- **Lightweight and private** - It only reads Steam’s local cache and only sends match IDs/salts to the API; no personal data. It runs with normal user permissions.

Install it once (Windows, Linux, Docker, or NixOS) and leave it running; then play Deadlock and submit matches as usual. See the [Deadlock API Ingest repo](https://github.com/deadlock-api/deadlock-api-ingest) for install scripts and details.

---

## Quickstart Guide

1. **Install the Deadlock world**
  - Use the **Deadlock** `.apworld` file, or place the `deadlock` folder in your Archipelago `worlds/` directory (see [Installation](#installation)).
2. **Create your options**
  - Use the **[Player Options](https://archipelagobrad.github.io/deadlockipelago/index.html)** web page to build a YAML and download it (recommended). It lets you set goal type, win counts, **game mode** (Standard or Street Brawl), **exclude hard locations**, starting heroes, and for **Win with Character** your final character and Spirits to unlock them.
  - (not recommended) Or in the Archipelago Launcher: **Generate Template Options** → choose **Deadlock** and configure options manually.
3. **Generate a multiworld**
  - Create a new multiworld (solo or with others), add **Deadlock** with your options, and generate the seed. Note the **room connection details** (server, port, password/slot).
4. **Run the Deadlock client**
  - From the Archipelago Launcher: open the **Deadlock Client** (or run the client from source if you installed the world manually).
  - Connect using the room URI or by entering server address and slot/password.
5. **Set your SteamID3**
  - In the client, run:  
   `/set_player_id [U:1:123456789]` or `/set_player_id 123456789`  
   (replace with your SteamID3 - I'd recommend [STEAMID I/O](https://steamid.io/) to fetch this.)
6. **Play Deadlock and submit matches**
  - Play matches in Deadlock. When a match has finished and is available via the match API, get its **match ID** from your Deadlock match history.
  - In the client:  
  `/submit_match <match_id>`  
  (aliases: `/submit`, `/s`).  
  - The client will fetch match data, award any earned locations, and update your progress. **Match data can take around 5 minutes (or more) to appear in the API even with [Deadlock API Ingest](https://github.com/deadlock-api/deadlock-api-ingest) running-if `/submit_match` fails, wait and try again.**
  - When you meet the goal, the client will report completion and send the goal to the server.
7. **Track progress**
  - `/goal` - current goal and progress  
  - `/heroes` - heroes unlocked via Archipelago items  
  - `/stats` - cumulative games submitted, kills, assists, souls, etc.

---

## Installation

### Option A: APWorld (recommended for players)

1. Obtain the `deadlock.apworld` file (from releases or from building the world).
2. In the Archipelago Launcher: **Options** → **Install APWorld** (or drag the `.apworld` into the launcher, depending on version).
3. The world and **Deadlock Client** will appear in the launcher.

### Option B: Source install (developers / custom builds)

1. Clone or copy this repository.
2. Copy the `deadlock` folder into your Archipelago install’s `worlds/` directory:
  `Archipelago/worlds/deadlock/`
3. Ensure the `deadlock` package contains at least: `__init__.py`, `Client.py`, `options.py`, `items.py`, `locations.py`, `regions.py`, `rules.py`, `data/`, `docs/`.
4. Restart the Archipelago Launcher; **Deadlock** and **Deadlock Client** should be available.

---

## Game Options


| Option                                | Description                                                                                                                                                                                                                                                              |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Goal Type**                         | **Unique Characters** – win with N different heroes; **Total Wins** – win N matches total; **Spirits (MacGuffin)** – collect N Spirits to win; **Win with Character** – collect X Spirits to unlock your chosen final character, then win one match with that character. |
| **Unique Characters to Win**          | Number of unique heroes you must win with (1–38). Used when Goal Type is Unique Characters.                                                                                                                                                                              |
| **Total Wins to Win**                 | Number of total match wins required (1–100). Used when Goal Type is Total Wins.                                                                                                                                                                                          |
| **Spirits to Win**                    | Number of Spirits you must collect to win. Max depends on **Game Mode** and **Exclude Hard Locations** (e.g. 162 Standard, 135 Standard with hard excluded, 143 Street Brawl, 119 Street Brawl with hard excluded). Used when Goal Type is Spirits.                      |
| **Spirits to Unlock Final Character** | Number of Spirits you must collect before your final character unlocks. Same max rules as Spirits to Win. Used when Goal Type is Win with Character.                                                                                                                     |
| **Final Character (Win With)**        | The hero you must win with to complete the run (Win with Character goal). Cannot be one of your starting heroes. Can be set to **Random** so one is chosen at download time (never a starting hero).                                                                     |
| **Game Mode**                         | **Standard** or **Street Brawl**. Only locations for the selected mode exist in the seed. Street Brawl has fewer, tuned-down checks and its own set of Street Brawl–only locations.                                                                                      |
| **Exclude Hard Locations**            | When enabled, harder checks (e.g. MVP/Key Player in many matches, high kills/assists/damage, fast round wins, win without dying) are removed from the seed. Lowers the number of locations and thus the maximum Spirits you can set.                                     |
| **Starting Heroes**                   | Optional: choose 3 starting heroes or “Random” so 3 are chosen when generating the YAML. For **Win with Character**, if you use Random starters, your final character is never one of the three.                                                                         |


Additional Archipelago options (e.g. Local Items, Non-Local Items) can be set in the template or in the player options YAML as needed.

---

## Items & Locations

### Items

- **Unlock [Hero]** - One item per hero (e.g. Unlock Abrams, Unlock Seven, Unlock Wraith). You receive these from the multiworld; each one allows you to **pick that hero** in Deadlock. You must have unlocked a hero before you can submit a match played as them and earn the corresponding “Win a game as [Hero]” locations. There are **38 hero-unlock items**.
- **Spirits** - MacGuffin item used to pad the pool and for **Spirits** and **Win with Character** goals. When your goal is **Spirits**, you win by collecting the configured number of Spirits. When your goal is **Win with Character**, you must collect the configured number of Spirits to *unlock* your final character (that hero is not in the item pool – you get them when you reach the threshold), then win one match with them to complete. Spirits are never placed in excluded locations, so seeds remain winnable even if you use location exclusions. The maximum Spirits you can set depends on game mode and whether **Exclude Hard Locations** is on (fewer locations = lower max).

The pool is padded with Spirits so the number of items matches the number of locations. The **Goal** location is locked to a victory item; when your goal is Spirits or Win with Character, the client sends the Goal check once you have met the condition (enough Spirits, or a win with your final character after enough Spirits).

### Locations

Locations are checked by the client when you submit matches (`/submit_match <match_id>`). Progress is cumulative from the start of your Archipelago save for that seed. Which locations exist depends on **Game Mode** (Standard vs Street Brawl) and **Exclude Hard Locations** (when on, harder checks are removed and the total location count is lower).

**Shared (both modes):** Hero wins, matches played, wins, kills, assists, Key Player, MVP, player damage.

**Standard only** (not in Street Brawl seeds): Soul Urn, neutral camps, Sinner's Sacrifice jackpots, souls, boss damage, denies, last hits.

**Street Brawl only** (only in Street Brawl seeds): Win 5/10/25/50 Street Brawl rounds; win a round in under 1m 30s or under 2m; win a match 3-0; win a match in under 7m or 10m; win without dying; win with 10+ kills.


| Category               | Examples                                                                                                                                                         |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hero wins**          | Win a game as [Hero] (Reward 1/3, 2/3, 3/3) for each of the 38 heroes. Requires that hero to be unlocked.                                                        |
| **Matches played**     | Complete 5, 10, 20, 50 matches.                                                                                                                                  |
| **Wins**               | Win 1 match; Win 5 / 10 / 15 / 20 / 25 matches (Reward 1/5 through 5/5 at each tier).                                                                            |
| **Soul Urn**           | Deliver the Soul Urn (in-game accolade). *Standard only.*                                                                                                        |
| **Neutral camps**      | Kill 1, 5, 10, 25, 50, 100 neutral camps. *Standard only.*                                                                                                       |
| **Sinner's Sacrifice** | Jackpots at 25, 50, 100, 250. *Standard only.*                                                                                                                   |
| **Kills**              | Kill 1, 10, 25, 50, 100, 250 enemy heroes.                                                                                                                       |
| **Assists**            | Get 1, 10, 25, 50, 100, 250 assists.                                                                                                                             |
| **Souls**              | Earn 10k, 50k, 100k, 250k, 500k, 1m souls (net worth). *Standard only.*                                                                                          |
| **Key Player**         | Be a Key Player (MVP rank 1, 2, or 3) in 5, 10, 25 matches.                                                                                                      |
| **MVP**                | Be the MVP (rank 1) in 1, 3, 5 matches.                                                                                                                          |
| **Boss damage**        | Deal 10k, 25k, 50k, 100k total; or 5k, 10k in a single match. *Standard only.*                                                                                   |
| **Player damage**      | Deal 100k, 250k, 500k, 1m total; or 10k, 20k, 30k in a single match.                                                                                             |
| **Denies**             | Get 10, 25, 50 denies. *Standard only.*                                                                                                                          |
| **Last hits**          | Get 250, 500, 1k, 2k last hits. *Standard only.*                                                                                                                 |
| **Street Brawl**       | Round wins (5, 10, 25, 50); round under 90s/2m; match 3-0; match under 7m/10m; win without dying; win with 10+ kills. *Street Brawl only.*                       |
| **Goal**               | Checked automatically when you meet your win condition (unique characters, total wins, enough Spirits, or a win with your final character after enough Spirits). |


---

## Client Usage

The Deadlock client connects to an Archipelago room and tracks your progress using match data from the Deadlock API.

If you **connect and have no characters unlocked** (e.g. you didn’t set starting heroes in your options), the client will show a one-time message telling you to create your YAML with the [Player Options generator](https://archipelagobrad.github.io/deadlockipelago/index.html) and regenerate the multiworld so you receive Unlock items.

### Essential commands


| Command                     | Description                                                                                                                                                |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/set_player_id <SteamID3>` | Set your SteamID3 (e.g. `[U:1:123456789]` or `123456789`). Required before submitting matches.                                                             |
| `/submit_match <match_id>`  | Submit a match by ID; fetches data from the API and sends earned location checks. Aliases: `/submit`, `/s`.                                                |
| `/goal`                     | Show the current goal and how close you are. For **Win with Character**, shows “Win with: [hero]” and Spirits progress.                                    |
| `/heroes`                   | List heroes unlocked via received Archipelago items. For **Win with Character**, your final character appears here once you have collected enough Spirits. |
| `/stats`                    | Show games submitted, kills, assists, souls, and related totals for this save.                                                                             |


### Match IDs

Match data is fetched from `https://api.deadlock-api.com/v1/matches/<match_id>/metadata`. You need the **match ID** for each match you want to submit (e.g. from your Deadlock match history or other match-history tools). Only matches that **started after** you created your Archipelago save for this seed can be submitted. **Using [Deadlock API Ingest](https://github.com/deadlock-api/deadlock-api-ingest) to submit your matches to the API is strongly recommended** so that `/submit_match` can fetch them reliably and you avoid missing-data failures.

### Completion

When you meet your goal, the client will send the **Goal** location check and a status update to the server so the multiworld marks your game as complete:

- **Unique Characters** or **Total Wins** – The client checks your save (unique heroes won / total wins) after each submitted match and sends Goal when the threshold is reached.
- **Spirits** – The client counts Spirits you have received from the multiworld. When your count reaches the required number (or you receive a new batch that pushes you over), it sends the Goal check. You can also trigger the check by submitting any match.
- **Win with Character** – You must first collect the required number of Spirits (your final character then counts as unlocked for submitting matches). Once you **win a match** with that character, the client sends the Goal check. Use `/goal` to see “Win with: [hero]” and your Spirits progress; use `/heroes` to see when your final character is available.

---

## Documentation

- **Setup (in-world):** `deadlock/docs/setup_en.md` - short setup steps and goals.
- **Game info (in-world):** `deadlock/docs/en_Deadlock.md` - overview of the world (locations, items, integration).

For Archipelago docs, see the [Archipelago documentation](https://github.com/ArchipelagoMW/Archipelago/tree/main/docs) and [archipelago.gg](https://archipelago.gg/).

---

## Credits

- **ArchipelagoBrad:** Archipelago client integration & logic
- **Manuel Hexe:** Developing the [unofficial Deadlock API](https://deadlock-api.com/) ([Please support him here!](https://www.patreon.com/manuelhexe))

---

Note: This is a fan-made AP implementation and is not affiliated with or endorsed by Valve or the Deadlock developers.
