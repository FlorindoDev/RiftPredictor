from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from riot_fetch.client_riot.constants import (
    APEX_ENDPOINTS,
    APEX_TIERS,
    DIVISIONS,
    METAL_TIERS,
    PLATFORM_TO_ROUTING_REGION,
    QUEUE_ALIASES,
    QUEUE_TO_MATCH_QUEUE,
)


@dataclass(frozen=True)
class Settings:
    api_key: str
    platform_region: str
    routing_region: str
    user_agent: str
    queue: str
    output_dir: Path
    match_count: int
    max_league_pages: int | None
    max_players: int | None
    max_match_pages_per_player: int | None
    match_queue: int | None
    match_type: str | None
    start_time: int | None
    end_time: int | None
    save_raw_responses: bool
    timeout: float


class SlidingWindowRateLimiter:
    def __init__(self, rules: tuple[tuple[int, float], ...]) -> None:
        self.rules = tuple((limit, window, deque()) for limit, window in rules)

    def wait(self) -> None:
        while True:
            now = time.monotonic()
            sleep_for = 0.0

            for limit, window, timestamps in self.rules:
                while timestamps and now - timestamps[0] >= window:
                    timestamps.popleft()
                if len(timestamps) >= limit:
                    sleep_for = max(sleep_for, window - (now - timestamps[0]))

            if sleep_for <= 0:
                break

            time.sleep(sleep_for + 0.01)

        now = time.monotonic()
        for _, _, timestamps in self.rules:
            timestamps.append(now)


class RiotApiError(RuntimeError):
    def __init__(self, status_code: int, url: str, body: str) -> None:
        super().__init__(f"Riot API error {status_code}: {url}\n{body}")
        self.status_code = status_code
        self.url = url
        self.body = body


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scarica giocatori dalla ladder Riot e match id per ogni PUUID, "
            "salvando i JSON sotto data/."
        ),
    )
    parser.add_argument(
        "--platform",
        help="Platform routing Riot, es. EUW1, EUN1, NA1, KR. Default: RIOT_PLATFORM_REGION.",
    )
    parser.add_argument(
        "--queue",
        default="RANKED_SOLO_5x5",
        help="Queue league-v4. Default: RANKED_SOLO_5x5.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Cartella base di output. Default: data.",
    )
    parser.add_argument(
        "--run-name",
        help="Nome sottocartella dentro output-dir. Default: timestamp.",
    )
    parser.add_argument(
        "--match-count",
        type=int,
        default=100,
        help="Numero match id per richiesta match-v5, massimo 100. Default: 100.",
    )
    parser.add_argument(
        "--max-league-pages",
        "--max-pages-per-rank",
        dest="max_league_pages",
        type=int,
        help=(
            "Limite pagine per ogni rank/divisione, es. IRON I, IRON II. "
            "Utile per test o raccolte bilanciate."
        ),
    )
    parser.add_argument(
        "--max-players",
        type=int,
        help="Limite totale giocatori. Utile per test.",
    )
    parser.add_argument(
        "--max-match-pages-per-player",
        type=int,
        help="Limite pagine match per giocatore. Default: nessun limite.",
    )
    parser.add_argument(
        "--match-queue",
        type=int,
        help=(
            "Filtro queueId match-v5. Default: 420 per RANKED_SOLO_5x5, "
            "440 per RANKED_FLEX_SR."
        ),
    )
    parser.add_argument(
        "--match-type",
        choices=("ranked", "normal", "tourney", "tutorial"),
        help="Filtro type match-v5. Default: ranked.",
    )
    parser.add_argument(
        "--start-time",
        type=int,
        help="Filtro startTime match-v5 in Unix seconds.",
    )
    parser.add_argument(
        "--end-time",
        type=int,
        help="Filtro endTime match-v5 in Unix seconds.",
    )
    parser.add_argument(
        "--no-raw-responses",
        action="store_true",
        help="Non salva le singole risposte raw; salva solo gli aggregati.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout HTTP in secondi. Default: 30.",
    )
    return parser.parse_args()


def load_settings(args: argparse.Namespace) -> Settings:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("RIOT_API_KEY", "").strip()
    platform_region = (args.platform or os.getenv("RIOT_PLATFORM_REGION", "")).strip().upper()
    user_agent = os.getenv(
        "RIOT_USER_AGENT",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    ).strip()

    if not api_key:
        raise ValueError("RIOT_API_KEY mancante in .env o nell'ambiente.")
    if not platform_region:
        raise ValueError("RIOT_PLATFORM_REGION mancante in .env oppure usa --platform.")
    if platform_region not in PLATFORM_TO_ROUTING_REGION:
        valid = ", ".join(sorted(PLATFORM_TO_ROUTING_REGION))
        raise ValueError(f"Platform non supportata: {platform_region}. Valori: {valid}")
    queue = QUEUE_ALIASES.get(args.queue.strip(), QUEUE_ALIASES.get(args.queue.strip().upper()))
    if not queue:
        valid_queues = ", ".join(sorted({"RANKED_SOLO_5x5", "RANKED_FLEX_SR"}))
        raise ValueError(f"Queue non supportata: {args.queue}. Valori: {valid_queues}")
    if not 1 <= args.match_count <= 100:
        raise ValueError("--match-count deve essere tra 1 e 100.")
    if args.max_league_pages is not None and args.max_league_pages < 1:
        raise ValueError("--max-pages-per-rank deve essere almeno 1.")
    match_queue = args.match_queue
    if match_queue is None:
        match_queue = QUEUE_TO_MATCH_QUEUE[queue]
    match_type = args.match_type or "ranked"

    run_name = args.run_name or datetime.now(timezone.utc).strftime(
        "riot_ladder_%Y%m%d_%H%M%S",
    )
    output_dir = args.output_dir / run_name

    return Settings(
        api_key=api_key,
        platform_region=platform_region,
        routing_region=PLATFORM_TO_ROUTING_REGION[platform_region],
        user_agent=user_agent,
        queue=queue,
        output_dir=output_dir,
        match_count=args.match_count,
        max_league_pages=args.max_league_pages,
        max_players=args.max_players,
        max_match_pages_per_player=args.max_match_pages_per_player,
        match_queue=match_queue,
        match_type=match_type,
        start_time=args.start_time,
        end_time=args.end_time,
        save_raw_responses=not args.no_raw_responses,
        timeout=args.timeout,
    )


def platform_host(platform_region: str) -> str:
    return f"{platform_region.lower()}.api.riotgames.com"


def routing_host(routing_region: str) -> str:
    return f"{routing_region.lower()}.api.riotgames.com"


def safe_path_component(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    safe = "".join(
        char if char.isalnum() or char in "._-" else "_"
        for char in text
    )
    return safe or fallback


def player_tier(player: dict[str, Any]) -> str:
    return safe_path_component(player.get("tier"), "UNKNOWN").upper()


def player_file_id(player: dict[str, Any]) -> str:
    return safe_path_component(
        player.get("puuid")
        or player.get("summonerId")
        or player.get("summonerName"),
    )


def player_match_ids_file(settings: Settings, player: dict[str, Any]) -> Path:
    return (
        settings.output_dir
        / "match_ids_by_tier"
        / player_tier(player)
        / f"{player_file_id(player)}.json"
    )


def raw_match_ids_file(settings: Settings, player: dict[str, Any], start: int) -> Path:
    return (
        settings.output_dir
        / "raw"
        / "match_ids"
        / player_tier(player)
        / f"match-{start:06d}-{player_file_id(player)}.json"
    )


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_path.replace(path)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def try_load_cached_json(path: Path) -> Any | None:
    try:
        return load_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"Cache JSON non valida, la rigenero: {path} ({exc})")
        return None


def build_url(host: str, path: str, params: dict[str, Any] | None = None) -> str:
    url = f"https://{host}{path}"
    clean_params = {
        key: value
        for key, value in (params or {}).items()
        if value is not None
    }
    if clean_params:
        url = f"{url}?{urlencode(clean_params)}"
    return url


def parse_retry_after(value: str | None) -> float:
    if not value:
        return 120.0
    try:
        return max(float(value), 1.0)
    except ValueError:
        return 120.0


def riot_get_json(
    host: str,
    path: str,
    params: dict[str, Any] | None,
    settings: Settings,
    limiter: SlidingWindowRateLimiter,
    max_retries: int = 5,
) -> Any:
    url = build_url(host, path, params)
    request = Request(
        url,
        headers={
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com",
            "X-Riot-Token": settings.api_key,
        },
    )

    for attempt in range(max_retries + 1):
        limiter.wait()
        try:
            with urlopen(request, timeout=settings.timeout) as response:
                payload = response.read().decode("utf-8")
                if not payload:
                    return None
                try:
                    return json.loads(payload)
                except json.JSONDecodeError as exc:
                    snippet = payload[:200].replace("\n", "\\n").replace("\r", "\\r")
                    raise RuntimeError(
                        f"Risposta non JSON da Riot per {url}: {exc}. "
                        f"Inizio risposta: {snippet!r}"
                    ) from exc
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt < max_retries:
                retry_after = parse_retry_after(exc.headers.get("Retry-After"))
                print(f"Rate limit Riot 429: pausa {retry_after:.1f}s")
                time.sleep(retry_after + 0.5)
                continue
            if 500 <= exc.code < 600 and attempt < max_retries:
                sleep_for = min(2**attempt, 60)
                print(f"Errore Riot {exc.code}: retry tra {sleep_for}s")
                time.sleep(sleep_for)
                continue
            raise RiotApiError(exc.code, url, body) from exc
        except URLError as exc:
            if attempt < max_retries:
                sleep_for = min(2**attempt, 60)
                print(f"Errore rete: retry tra {sleep_for}s ({exc.reason})")
                time.sleep(sleep_for)
                continue
            raise RuntimeError(f"Errore rete su {url}: {exc}") from exc

    raise RuntimeError(f"Retry esauriti per {url}")


def league_entries_path(queue: str, tier: str, division: str) -> str:
    return (
        "/lol/league/v4/entries/"
        f"{quote(queue, safe='')}/"
        f"{quote(tier, safe='')}/"
        f"{quote(division, safe='')}"
    )


def match_ids_path(puuid: str) -> str:
    return f"/lol/match/v5/matches/by-puuid/{quote(puuid, safe='')}/ids"


def apex_league_path(tier: str, queue: str) -> str:
    endpoint = APEX_ENDPOINTS[tier]
    return f"/lol/league/v4/{endpoint}/by-queue/{quote(queue, safe='')}"


def fetch_league_entries(
    settings: Settings,
    limiter: SlidingWindowRateLimiter,
) -> list[dict[str, Any]]:
    players_path = settings.output_dir / "players.json"
    if players_path.exists():
        players = load_json(players_path)
        print(f"Giocatori caricati da {players_path}: {len(players)}")
        return players

    players_by_puuid: dict[str, dict[str, Any]] = {}
    host = platform_host(settings.platform_region)

    for tier in METAL_TIERS:
        for division in DIVISIONS:
            page = 1
            while True:
                raw_path = (
                    settings.output_dir
                    / "raw"
                    / "league_entries"
                    / settings.queue
                    / tier
                    / f"{division}_page_{page:04d}.json"
                )
                if raw_path.exists():
                    entries = load_json(raw_path)
                else:
                    entries = riot_get_json(
                        host=host,
                        path=league_entries_path(settings.queue, tier, division),
                        params={"page": page},
                        settings=settings,
                        limiter=limiter,
                    )
                    if settings.save_raw_responses:
                        save_json(raw_path, entries)

                if not entries:
                    print(f"{tier} {division}: fine a pagina {page}")
                    break

                for entry in entries:
                    enriched = dict(entry)
                    enriched.setdefault("tier", tier)
                    enriched.setdefault("rank", division)
                    enriched.setdefault("queueType", settings.queue)
                    puuid = enriched.get("puuid")
                    if puuid and puuid not in players_by_puuid:
                        players_by_puuid[puuid] = enriched

                print(
                    f"{tier} {division} pagina {page}: "
                    f"+{len(entries)} entry, totale giocatori {len(players_by_puuid)}"
                )

                if settings.max_players and len(players_by_puuid) >= settings.max_players:
                    players = list(players_by_puuid.values())[: settings.max_players]
                    save_json(settings.output_dir / "players.json", players)
                    return players

                if settings.max_league_pages and page >= settings.max_league_pages:
                    break

                page += 1

    fetch_apex_league_entries(settings, limiter, players_by_puuid)

    players = list(players_by_puuid.values())
    save_json(settings.output_dir / "players.json", players)
    return players


def fetch_apex_league_entries(
    settings: Settings,
    limiter: SlidingWindowRateLimiter,
    players_by_puuid: dict[str, dict[str, Any]],
) -> None:
    host = platform_host(settings.platform_region)

    for tier in APEX_TIERS:
        raw_path = (
            settings.output_dir
            / "raw"
            / "league_entries"
            / settings.queue
            / tier
            / "league.json"
        )
        if raw_path.exists():
            league = load_json(raw_path)
        else:
            league = riot_get_json(
                host=host,
                path=apex_league_path(tier, settings.queue),
                params=None,
                settings=settings,
                limiter=limiter,
            )
            if settings.save_raw_responses:
                save_json(raw_path, league)

        entries = league.get("entries", []) if isinstance(league, dict) else []
        for entry in entries:
            enriched = dict(entry)
            enriched.setdefault("tier", league.get("tier", tier))
            enriched.setdefault("rank", "I")
            enriched.setdefault("queueType", league.get("queue", settings.queue))
            enriched.setdefault("leagueId", league.get("leagueId"))
            puuid = enriched.get("puuid")
            if puuid and puuid not in players_by_puuid:
                players_by_puuid[puuid] = enriched

        print(f"{tier}: +{len(entries)} entry, totale giocatori {len(players_by_puuid)}")


def match_query_params(settings: Settings, start: int) -> dict[str, Any]:
    return {
        "start": start,
        "count": settings.match_count,
        "queue": settings.match_queue,
        "type": settings.match_type,
        "startTime": settings.start_time,
        "endTime": settings.end_time,
    }


def match_query_signature(settings: Settings) -> dict[str, Any]:
    return {
        "match_count": settings.match_count,
        "match_queue": settings.match_queue,
        "match_type": settings.match_type,
        "start_time": settings.start_time,
        "end_time": settings.end_time,
    }


def cached_match_result_is_current(
    result: Any,
    settings: Settings,
) -> bool:
    return (
        isinstance(result, dict)
        and result.get("match_query") == match_query_signature(settings)
    )


def fetch_player_match_ids(
    player: dict[str, Any],
    settings: Settings,
    limiter: SlidingWindowRateLimiter,
) -> dict[str, Any]:
    puuid = player["puuid"]
    player_path = player_match_ids_file(settings, player)
    if player_path.exists():
        cached_result = try_load_cached_json(player_path)
        if cached_match_result_is_current(cached_result, settings):
            result = cached_result
            return result

    host = routing_host(settings.routing_region)
    match_ids: list[str] = []
    page_number = 0
    start = 0

    while True:
        raw_path = raw_match_ids_file(settings, player, start)
        ids = riot_get_json(
            host=host,
            path=match_ids_path(puuid),
            params=match_query_params(settings, start),
            settings=settings,
            limiter=limiter,
        )
        if settings.save_raw_responses:
            save_json(raw_path, ids)

        if not ids:
            break

        match_ids.extend(ids)
        page_number += 1

        if len(ids) < settings.match_count:
            break
        if (
            settings.max_match_pages_per_player
            and page_number >= settings.max_match_pages_per_player
        ):
            break

        start += settings.match_count

    result = {
        "puuid": puuid,
        "tier": player_tier(player),
        "match_query": match_query_signature(settings),
        "player": player,
        "match_ids": match_ids,
        "match_count": len(match_ids),
    }
    save_json(player_path, result)
    return result


def fetch_all_match_ids(
    players: list[dict[str, Any]],
    settings: Settings,
    limiter: SlidingWindowRateLimiter,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    total_players = len(players)

    for index, player in enumerate(players, start=1):
        puuid = player.get("puuid")
        if not puuid:
            continue

        result = fetch_player_match_ids(player, settings, limiter)
        results.append(result)
        tier = result.get("tier", player_tier(player))
        print(
            f"Giocatore {index}/{total_players}: "
            f"{tier} - {result['match_count']} match id"
        )

    unique_match_ids = sorted(
        {
            match_id
            for result in results
            for match_id in result.get("match_ids", [])
        },
    )
    save_json(settings.output_dir / "match_ids_unique.json", unique_match_ids)
    return results


def write_manifest(settings: Settings) -> None:
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform_region": settings.platform_region,
        "routing_region": settings.routing_region,
        "user_agent": settings.user_agent,
        "queue": settings.queue,
        "match_count": settings.match_count,
        "max_league_pages": settings.max_league_pages,
        "max_pages_per_rank": settings.max_league_pages,
        "max_players": settings.max_players,
        "max_match_pages_per_player": settings.max_match_pages_per_player,
        "match_queue": settings.match_queue,
        "match_type": settings.match_type,
        "start_time": settings.start_time,
        "end_time": settings.end_time,
        "save_raw_responses": settings.save_raw_responses,
        "rate_limits": {
            "short_window": "20 requests / 1 second",
            "long_window": "200 requests / 120 seconds",
        },
        "outputs": {
            "players": "players.json",
            "match_ids_by_tier": "match_ids_by_tier/",
            "match_ids_unique": "match_ids_unique.json",
            "raw_match_ids": "raw/match_ids/<TIER>/match-<start>-<player_id>.json",
            "raw_responses": "raw/",
        },
    }
    save_json(settings.output_dir / "manifest.json", manifest)


def main() -> int:
    args = parse_args()

    try:
        settings = load_settings(args)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        write_manifest(settings)

        limiter = SlidingWindowRateLimiter(((20, 1.0), (200, 120.0)))

        print(f"Output: {settings.output_dir}")
        print(
            "League host: "
            f"{platform_host(settings.platform_region)} | "
            f"Match host: {routing_host(settings.routing_region)}"
        )

        players = fetch_league_entries(settings, limiter)
        print(f"Giocatori totali: {len(players)}")

        results = fetch_all_match_ids(players, settings, limiter)
        unique_count = len(
            {
                match_id
                for result in results
                for match_id in result.get("match_ids", [])
            },
        )
        print(f"Match id unici: {unique_count}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente. Puoi riusare --run-name per riprendere.")
        return 130
    except Exception as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
