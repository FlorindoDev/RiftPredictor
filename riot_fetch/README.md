# riot_fetch

## Index

- [English Version](#english-version)
- [Versione Italiana](#versione-italiana)

<a id="english-version"></a>

## English Version

## download_ladder_match_ids.py

Script that downloads ranked players from the Riot API and then downloads
available match ids for each player through their PUUID.

Run it from the project root:

```powershell
python riot_fetch/download_ladder_match_ids.py
```

Or as a module:

```powershell
python -m riot_fetch.download_ladder_match_ids
```

## Requirements

The `.env` file must be in the project root and must contain:

```env
RIOT_API_KEY=your_api_key
RIOT_PLATFORM_REGION=EUW1
```

Optional, if Cloudflare blocks the client:

```env
RIOT_USER_AGENT=Mozilla/5.0 ...
```

## What It Does

1. Downloads ranked players with `league-v4`.
2. For `IRON` through `DIAMOND`, it uses:

```text
/lol/league/v4/entries/{queue}/{tier}/{division}?page={page}
```

3. For `MASTER`, `GRANDMASTER`, and `CHALLENGER`, it uses Riot's dedicated
   league endpoints.
4. Reads each player's `puuid`.
5. Downloads match ids with `match-v5`:

```text
/lol/match/v5/matches/by-puuid/{puuid}/ids
```

6. Saves JSON files under `data/`.

The script respects these rate limits:

```text
20 requests / second
200 requests / 120 seconds
```

It also handles `429` responses using `Retry-After`.

## Output

Each run creates a subfolder:

```text
data/riot_ladder_YYYYMMDD_HHMMSS/
```

Or, if you use `--run-name`:

```text
data/run_name/
```

Main files:

```text
manifest.json
```

Run settings.

```text
players.json
```

Aggregated list of ranked players found.

```text
match_ids_unique.json
```

Flat list of unique match ids.

```text
match_ids_by_tier/
```

One JSON file per player, grouped by tier. File names use the player PUUID.

```text
raw/
```

Original Riot responses, unless you use `--no-raw-responses`.
Match-id pages are saved as
`raw/match_ids/<TIER>/match-000200-<PUUID>.json`.

## Resume

To resume an interrupted run, launch the script again with the same run name:

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name euw_collection
```

Resume works best when raw responses are enabled, so avoid
`--no-raw-responses` if you want reliable resume behavior.

## Command Reference

```text
usage: download_ladder_match_ids.py [-h] [--platform PLATFORM] [--queue QUEUE]
                                    [--output-dir OUTPUT_DIR]
                                    [--run-name RUN_NAME]
                                    [--match-count MATCH_COUNT]
                                    [--max-league-pages MAX_LEAGUE_PAGES]
                                    [--max-players MAX_PLAYERS]
                                    [--max-match-pages-per-player MAX_MATCH_PAGES_PER_PLAYER]
                                    [--match-queue MATCH_QUEUE]
                                    [--match-type {ranked,normal,tourney,tutorial}]
                                    [--start-time START_TIME]
                                    [--end-time END_TIME]
                                    [--no-raw-responses]
                                    [--timeout TIMEOUT]
```

### `--platform PLATFORM`

Riot platform routing region. Default: `RIOT_PLATFORM_REGION`.

Examples:

```powershell
python riot_fetch/download_ladder_match_ids.py --platform EUW1
python riot_fetch/download_ladder_match_ids.py --platform NA1
python riot_fetch/download_ladder_match_ids.py --platform KR
```

### `--queue QUEUE`

Ranked queue to download. Default: `RANKED_SOLO_5x5`.

Supported values:

```text
RANKED_SOLO_5x5
SOLO
RANKED_FLEX_SR
FLEX
```

Examples:

```powershell
python riot_fetch/download_ladder_match_ids.py --queue RANKED_SOLO_5x5
python riot_fetch/download_ladder_match_ids.py --queue RANKED_FLEX_SR
```

### `--output-dir OUTPUT_DIR`

Base output folder. Default: `data`.

```powershell
python riot_fetch/download_ladder_match_ids.py --output-dir data
```

### `--run-name RUN_NAME`

Name of the run subfolder. Also used to resume a run.

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name euw_collection
```

### `--match-count MATCH_COUNT`

Number of match ids per `match-v5` request. Riot maximum: `100`.
Default: `100`.

```powershell
python riot_fetch/download_ladder_match_ids.py --match-count 100
```

### `--max-league-pages`, `--max-pages-per-rank`

Page limit for each rank/division, for example `IRON I` or `BRONZE IV`.

```powershell
python riot_fetch/download_ladder_match_ids.py --max-pages-per-rank 5
```

### `--max-players MAX_PLAYERS`

Total player limit. Useful if you want to reach the match-id phase earlier.

```powershell
python riot_fetch/download_ladder_match_ids.py --max-players 1000
```

### `--max-match-pages-per-player MAX_MATCH_PAGES_PER_PLAYER`

Match page limit for each player. Each page can contain up to 100 match ids.

```powershell
python riot_fetch/download_ladder_match_ids.py --max-match-pages-per-player 1
```

### `--match-queue MATCH_QUEUE`

`queueId` filter for match ids. Default: `420` for ranked solo/duo,
`440` for ranked flex.

```powershell
python riot_fetch/download_ladder_match_ids.py --match-queue 420
```

### `--match-type ranked|normal|tourney|tutorial`

Match type filter. Default: `ranked`.

```powershell
python riot_fetch/download_ladder_match_ids.py --match-type ranked
```

### `--start-time START_TIME`

Start filter in Unix timestamp seconds.

```powershell
python riot_fetch/download_ladder_match_ids.py --start-time 1704067200
```

### `--end-time END_TIME`

End filter in Unix timestamp seconds.

```powershell
python riot_fetch/download_ladder_match_ids.py --end-time 1735689600
```

### `--no-raw-responses`

Do not save raw Riot responses. Not recommended if you want reliable resume
behavior.

```powershell
python riot_fetch/download_ladder_match_ids.py --no-raw-responses
```

### `--timeout TIMEOUT`

HTTP timeout in seconds. Default: `30`.

```powershell
python riot_fetch/download_ladder_match_ids.py --timeout 60
```

## Examples

Quick test:

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name test --max-pages-per-rank 1 --max-players 10 --max-match-pages-per-player 1
```

Limited but useful collection:

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name euw_collection --max-pages-per-rank 5 --max-players 1000 --max-match-pages-per-player 1
```

Ranked solo/duo only:

```powershell
python riot_fetch/download_ladder_match_ids.py --platform EUW1 --queue RANKED_SOLO_5x5 --match-queue 420 --match-type ranked --run-name euw_solo_ranked
```

Flex queue:

```powershell
python riot_fetch/download_ladder_match_ids.py --queue RANKED_FLEX_SR --run-name euw_flex
```

---

<a id="versione-italiana"></a>

## Versione Italiana

## download_ladder_match_ids.py

Script per scaricare giocatori ranked dalla Riot API e, per ogni giocatore,
scaricare gli id dei match disponibili tramite PUUID.

Va lanciato dalla root del progetto:

```powershell
python riot_fetch/download_ladder_match_ids.py
```

Oppure come modulo:

```powershell
python -m riot_fetch.download_ladder_match_ids
```

## Requisiti

Il file `.env` deve stare nella root del progetto e deve contenere:

```env
RIOT_API_KEY=la_tua_api_key
RIOT_PLATFORM_REGION=EUW1
```

Opzionale, se Cloudflare blocca il client:

```env
RIOT_USER_AGENT=Mozilla/5.0 ...
```

## Cosa fa

1. Scarica i giocatori ranked con `league-v4`.
2. Per `IRON` fino a `DIAMOND` usa:

```text
/lol/league/v4/entries/{queue}/{tier}/{division}?page={page}
```

3. Per `MASTER`, `GRANDMASTER`, `CHALLENGER` usa gli endpoint dedicati Riot.
4. Per ogni giocatore legge il `puuid`.
5. Scarica gli id dei match con `match-v5`:

```text
/lol/match/v5/matches/by-puuid/{puuid}/ids
```

6. Salva i JSON nella cartella `data/`.

Lo script rispetta questi limiti:

```text
20 richieste / secondo
200 richieste / 120 secondi
```

Gestisce anche `429` usando `Retry-After`.

## Output

Ogni run crea una sottocartella:

```text
data/riot_ladder_YYYYMMDD_HHMMSS/
```

Oppure, se usi `--run-name`:

```text
data/nome_run/
```

File principali:

```text
manifest.json
```

Impostazioni della run.

```text
players.json
```

Lista dei giocatori ranked trovati.

```text
match_ids_unique.json
```

Lista piatta di match id unici.

```text
match_ids_by_tier/
```

Un file per ogni giocatore, raggruppato per tier. Il nome del file usa il PUUID
del player.

```text
raw/
```

Risposte originali Riot, se non usi `--no-raw-responses`.
Le pagine dei match id vengono salvate come
`raw/match_ids/<TIER>/match-000200-<PUUID>.json`.

## Resume

Per riprendere una run interrotta, rilancia con lo stesso nome:

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name raccolta_euw
```

Il resume funziona meglio lasciando attivo il salvataggio `raw/`, quindi senza
`--no-raw-responses`.

## Manuale comandi

```text
usage: download_ladder_match_ids.py [-h] [--platform PLATFORM] [--queue QUEUE]
                                    [--output-dir OUTPUT_DIR]
                                    [--run-name RUN_NAME]
                                    [--match-count MATCH_COUNT]
                                    [--max-league-pages MAX_LEAGUE_PAGES]
                                    [--max-players MAX_PLAYERS]
                                    [--max-match-pages-per-player MAX_MATCH_PAGES_PER_PLAYER]
                                    [--match-queue MATCH_QUEUE]
                                    [--match-type {ranked,normal,tourney,tutorial}]
                                    [--start-time START_TIME]
                                    [--end-time END_TIME]
                                    [--no-raw-responses]
                                    [--timeout TIMEOUT]
```

### `--platform PLATFORM`

Platform routing Riot. Default: `RIOT_PLATFORM_REGION`.

Esempi:

```powershell
python riot_fetch/download_ladder_match_ids.py --platform EUW1
python riot_fetch/download_ladder_match_ids.py --platform NA1
python riot_fetch/download_ladder_match_ids.py --platform KR
```

### `--queue QUEUE`

Queue ranked da scaricare. Default: `RANKED_SOLO_5x5`.

Valori supportati:

```text
RANKED_SOLO_5x5
SOLO
RANKED_FLEX_SR
FLEX
```

Esempi:

```powershell
python riot_fetch/download_ladder_match_ids.py --queue RANKED_SOLO_5x5
python riot_fetch/download_ladder_match_ids.py --queue RANKED_FLEX_SR
```

### `--output-dir OUTPUT_DIR`

Cartella base di output. Default: `data`.

```powershell
python riot_fetch/download_ladder_match_ids.py --output-dir data
```

### `--run-name RUN_NAME`

Nome della sottocartella della run. Serve anche per riprendere.

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name raccolta_euw
```

### `--match-count MATCH_COUNT`

Numero di match id per richiesta `match-v5`. Massimo Riot: `100`.
Default: `100`.

```powershell
python riot_fetch/download_ladder_match_ids.py --match-count 100
```

### `--max-league-pages`, `--max-pages-per-rank`

Limite pagine per ogni rank/divisione, per esempio `IRON I` o `BRONZE IV`.

```powershell
python riot_fetch/download_ladder_match_ids.py --max-pages-per-rank 5
```

### `--max-players MAX_PLAYERS`

Limite totale giocatori. Utile per arrivare prima alla fase match id.

```powershell
python riot_fetch/download_ladder_match_ids.py --max-players 1000
```

### `--max-match-pages-per-player MAX_MATCH_PAGES_PER_PLAYER`

Limite pagine match per ogni giocatore. Ogni pagina puo contenere fino a 100
match id.

```powershell
python riot_fetch/download_ladder_match_ids.py --max-match-pages-per-player 1
```

### `--match-queue MATCH_QUEUE`

Filtro `queueId` per i match id. Default: `420` per ranked solo/duo,
`440` per ranked flex.

```powershell
python riot_fetch/download_ladder_match_ids.py --match-queue 420
```

### `--match-type ranked|normal|tourney|tutorial`

Filtro tipo match. Default: `ranked`.

```powershell
python riot_fetch/download_ladder_match_ids.py --match-type ranked
```

### `--start-time START_TIME`

Filtro iniziale in Unix timestamp seconds.

```powershell
python riot_fetch/download_ladder_match_ids.py --start-time 1704067200
```

### `--end-time END_TIME`

Filtro finale in Unix timestamp seconds.

```powershell
python riot_fetch/download_ladder_match_ids.py --end-time 1735689600
```

### `--no-raw-responses`

Non salva le risposte raw di Riot. Sconsigliato se vuoi poter riprendere bene
una run.

```powershell
python riot_fetch/download_ladder_match_ids.py --no-raw-responses
```

### `--timeout TIMEOUT`

Timeout HTTP in secondi. Default: `30`.

```powershell
python riot_fetch/download_ladder_match_ids.py --timeout 60
```

## Esempi

Test veloce:

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name test --max-pages-per-rank 1 --max-players 10 --max-match-pages-per-player 1
```

Raccolta limitata ma utile:

```powershell
python riot_fetch/download_ladder_match_ids.py --run-name raccolta_euw --max-pages-per-rank 5 --max-players 1000 --max-match-pages-per-player 1
```

Solo ranked solo/duo:

```powershell
python riot_fetch/download_ladder_match_ids.py --platform EUW1 --queue RANKED_SOLO_5x5 --match-queue 420 --match-type ranked --run-name euw_solo_ranked
```

Flex:

```powershell
python riot_fetch/download_ladder_match_ids.py --queue RANKED_FLEX_SR --run-name euw_flex
```
