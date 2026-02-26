<p align="center">
  <img src="./deadlock-portraits/deadlock_logo.png" alt="Deadlock Archipelago" width="600">
</p>

An [Archipelago](https://archipelago.gg/) world and client for **Deadlock** - a meta-progression randomizer where locations are earned by playing matches (hero wins, match milestones, accolades) and items unlock heroes you can use. Complete your goal (e.g. win with N unique characters or N total wins) to finish the seed.

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
   - Use the [**Player Options**](https://archipelagobrad.github.io/deadlockipelago/index.html) web page to build a YAML and download it.
   - (not recommended) Or in the Archipelago Launcher: **Generate Template Options** → choose **Deadlock** and configure goal type, win counts, and (optionally) starting heroes.

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

| Option | Description |
|--------|-------------|
| **Goal Type** | **Unique Characters** - win with N different heroes; **Total Wins** - win N matches total. |
| **Unique Characters to Win** | Number of unique heroes you must win with (1–38). Used when Goal Type is Unique Characters. |
| **Total Wins to Win** | Number of total match wins required (1–100). Used when Goal Type is Total Wins. |
| **Starting Heroes** | Optional: choose 3 starting heroes or “Random” so 3 are chosen when generating the YAML. |

Additional Archipelago options (e.g. Local Items, Non-Local Items) can be set in the template or in the player options YAML as needed.

---

## Items & Locations

### Items

All items are **progression** items that unlock playable heroes:

- **Unlock [Hero]** - One item per hero (e.g. Unlock Abrams, Unlock Seven, Unlock Wraith). You receive these from the multiworld; each one allows you to **pick that hero** in Deadlock. You must have unlocked a hero before you can submit a match played as them and earn the corresponding “Win a game as [Hero]” locations.

There are **38 hero-unlock items**. The pool is padded with filler items so the number of items matches the number of locations. The **Goal** location is locked to a victory item that is checked when you meet your win condition.

### Locations

Locations are checked by the client when you submit matches (`/submit_match <match_id>`). Progress is cumulative from the start of your Archipelago save for that seed. Types of locations:

| Category | Examples |
|----------|----------|
| **Hero wins** | Win a game as [Hero] (Reward 1/3, 2/3, 3/3) for each of the 38 heroes. Requires that hero to be unlocked. |
| **Matches played** | Complete 5, 10, 20, 50 matches. |
| **Wins** | Win 1 match; Win 5 / 10 / 15 / 20 / 25 matches (Reward 1/5 through 5/5 at each tier). |
| **Soul Urn** | Deliver the Soul Urn (in-game accolade). |
| **Neutral camps** | Kill 1, 5, 10, 25, 50, 100 neutral camps. |
| **Sinner's Sacrifice** | Jackpots at 25, 50, 100, 250. |
| **Kills** | Kill 1, 10, 25, 50, 100, 250 enemy heroes. |
| **Assists** | Get 1, 10, 25, 50, 100, 250 assists. |
| **Souls** | Earn 10k, 50k, 100k, 250k, 500k, 1m souls (net worth). |
| **Key Player** | Be a Key Player (MVP rank 1, 2, or 3) in 5, 10, 25 matches. |
| **MVP** | Be the MVP (rank 1) in 1, 3, 5 matches. |
| **Boss damage** | Deal 10k, 25k, 50k, 100k total; or 5k, 10k in a single match. |
| **Player damage** | Deal 100k, 250k, 500k, 1m total; or 10k, 20k, 30k in a single match. |
| **Denies** | Get 10, 25, 50 denies. |
| **Last hits** | Get 250, 500, 1k, 2k last hits. |
| **Goal** | Checked automatically when you meet your configured win condition (unique characters or total wins). |

---

## Client Usage

The Deadlock client connects to an Archipelago room and tracks your progress using match data from the Deadlock API.

### Essential commands

| Command | Description |
|---------|-------------|
| `/set_player_id <SteamID3>` | Set your SteamID3 (e.g. `[U:1:123456789]` or `123456789`). Required before submitting matches. |
| `/submit_match <match_id>` | Submit a match by ID; fetches data from the API and sends earned location checks. Aliases: `/submit`, `/s`. |
| `/goal` | Show the current goal and how close you are. |
| `/heroes` | List heroes unlocked via received Archipelago items. |
| `/stats` | Show games submitted, kills, assists, souls, and related totals for this save. |

### Match IDs

Match data is fetched from `https://api.deadlock-api.com/v1/matches/<match_id>/metadata`. You need the **match ID** for each match you want to submit (e.g. from your Deadlock match history or other match-history tools). Only matches that **started after** you created your Archipelago save for this seed can be submitted. **Using [Deadlock API Ingest](https://github.com/deadlock-api/deadlock-api-ingest) to submit your matches to the API is strongly recommended** so that `/submit_match` can fetch them reliably and you avoid missing-data failures.

### Completion

When you meet your goal (e.g. enough unique hero wins or total wins), the client will send the **Goal** location check and a status update to the server so the multiworld marks your game as complete.

---

## Documentation

- **Setup (in-world):** `deadlock/docs/setup_en.md` - short setup steps and goals.
- **Game info (in-world):** `deadlock/docs/en_Deadlock.md` - overview of the world (locations, items, integration).

For Archipelago docs, see the [Archipelago documentation](https://github.com/ArchipelagoMW/Archipelago/tree/main/docs) and [archipelago.gg](https://archipelago.gg/).

---

Note: This is a fan-made mod and is not affiliated with or endorsed by Valve or the Deadlock developers.
