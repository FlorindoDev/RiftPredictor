from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "riot_ladder_20260519_212022"
    / "match_ids_by_tier"
    / "IRON"
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from riot_fetch.client_riot import create_client, load_config
from riot_fetch.models import Match
from riot_fetch.services import MatchStatsService, RiotPlayerService, UtenteService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test manuale dei service Riot su un file giocatore locale.",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Calcola anche KDA e winrate sulle ultime 10 partite.",
    )
    parser.add_argument(
        "--lane",
        help="Lane da usare per la differenza rank. Default: lane del giocatore.",
    )
    return parser.parse_args()


def _get_first_player_file() -> Path:
    player_files = sorted(DATA_DIR.glob("*.json"))
    if not player_files:
        raise FileNotFoundError(f"Nessun file giocatore trovato in {DATA_DIR}")

    return player_files[0]


def _format_rank(rank_info: dict[str, Any] | None) -> str:
    if not rank_info:
        return "Unranked"

    return (
        f"{rank_info['rank_nome']} "
        f"({rank_info['league_points']} LP, score {rank_info['rank']})"
    )


def main() -> None:
    args = parse_args()
    player_file = _get_first_player_file()

    with player_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    config = load_config()
    client = create_client(config)

    utente_service = UtenteService(
        player=data["player"],
        match_ids=data["match_ids"],
        match_query=data["match_query"],
        config=config,
        client=client,
    )
    riot_player_service = RiotPlayerService(config=config, client=client)
    match_stats_service = MatchStatsService(
        config=config,
        client=client,
        riot_player_service=riot_player_service,
    )

    match_id = utente_service.match_ids[0]
    match = Match(match_id=match_id, config=config, client=client)
    giocatore = match.get_giocatore_by_puuid(utente_service.puuid)

    if not giocatore:
        raise ValueError(f"Giocatore {utente_service.puuid} non trovato in {match_id}")

    champion = riot_player_service.get_champion(giocatore)
    lane = args.lane or giocatore.team_position
    lane_rank_difference = match_stats_service.get_lane_rank_difference(
        match=match,
        lane=lane,
    )
    player_rank_info = (
        lane_rank_difference["blue_rank_info"]
        if giocatore.team_id == 100
        else lane_rank_difference["red_rank_info"]
    )
    mastery = champion["mastery"]
    rank_label = (
        "Rank player"
        if lane.upper() == giocatore.team_position
        else f"Rank {lane.upper()} team player"
    )

    print(f"File giocatore: {player_file.name}")
    print(f"PUUID: {utente_service.puuid}")
    print(f"Match riferimento: {match_id}")
    print(f"Champion: {giocatore.champion_name}")
    print(f"Lane: {lane}")
    print(f"{rank_label}: {_format_rank(player_rank_info)}")
    print(f"Champion mastery level: {mastery.get('championLevel', 0)}")
    print(f"Champion mastery points: {mastery.get('championPoints', 0)}")
    print(
        "Differenza rank lane: "
        f"{lane_rank_difference['rank_difference']} "
        f"(blue {lane_rank_difference['blue_rank']}, "
        f"red {lane_rank_difference['red_rank']})"
    )

    if args.history:
        stats = utente_service.get_kda_winrate_ultime_10(match_id)
        print(f"Partite usate: {stats['games_count']}")
        print(f"KDA medio ultime 10: {stats['avg_kda']}")
        print(f"Winrate ultime 10: {stats['winrate']}%")


if __name__ == "__main__":
    main()
