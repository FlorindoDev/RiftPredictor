from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from riot_fetch.client_riot import create_client, load_config
from riot_fetch.services.match_features_service import MatchFeaturesService
from riot_fetch.services.match_stats_service import MatchStatsService
from riot_fetch.services.riot_player_service import RiotPlayerService
from riot_fetch.services.utente_service import UtenteService


DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "riot_ladder_20260519_212022"
    / "match_ids_by_tier"
)

CSV_PATH = PROJECT_ROOT / "data" / "match_features.csv"
TEAM_POSITIONS = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")

CSV_FIELDNAMES = [
    "avg_rank_difference_player_team_vs_enemy",
    "avg_player_team_winrate",
    "avg_enemy_winrate",
    "ally_top_champion",
    "ally_top_champion_mastery",
    "ally_top_kda",
    "ally_jungle_champion",
    "ally_jungle_champion_mastery",
    "ally_jungle_kda",
    "ally_middle_champion",
    "ally_middle_champion_mastery",
    "ally_middle_kda",
    "ally_bottom_champion",
    "ally_bottom_champion_mastery",
    "ally_bottom_kda",
    "ally_utility_champion",
    "ally_utility_champion_mastery",
    "ally_utility_kda",
    "enemy_top_champion",
    "enemy_top_champion_mastery",
    "enemy_top_kda",
    "enemy_jungle_champion",
    "enemy_jungle_champion_mastery",
    "enemy_jungle_kda",
    "enemy_middle_champion",
    "enemy_middle_champion_mastery",
    "enemy_middle_kda",
    "enemy_bottom_champion",
    "enemy_bottom_champion_mastery",
    "enemy_bottom_kda",
    "enemy_utility_champion",
    "enemy_utility_champion_mastery",
    "enemy_utility_kda",
]


def load_match_files() -> list[tuple[Path, dict[str, Any]]]:
    json_files = sorted(DATA_DIR.rglob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"Nessun file JSON trovato in {DATA_DIR}")

    files = []
    for file_path in json_files:
        with file_path.open("r", encoding="utf-8") as file:
            files.append((file_path, json.load(file)))

    return files


def build_csv_row(features: dict[str, Any]) -> dict[str, Any]:
    personal_features = features["personal_features"]
    team_features = features["team_features"]
    enemy_features = features["enemy_features"]

    row = {
        "avg_rank_difference_player_team_vs_enemy": team_features[
            "avg_player_team_minus_enemy"
        ],
        "avg_player_team_winrate": team_features["avg_winrate"],
        "avg_enemy_winrate": enemy_features["avg_winrate"],
    }

    allies_by_position = {
        ally["team_position"].upper(): ally
        for ally in team_features["composition"]
    }
    for position in TEAM_POSITIONS:
        ally = allies_by_position.get(position, {})
        column_prefix = position.lower()
        row[f"ally_{column_prefix}_champion"] = ally.get("champion_name", "")
        row[f"ally_{column_prefix}_champion_mastery"] = ally.get(
            "champion_mastery",
            0,
        )
        row[f"ally_{column_prefix}_kda"] = ally.get("kda", 0)

    enemies_by_position = {
        enemy["team_position"].upper(): enemy
        for enemy in enemy_features["composition"]
    }
    for position in TEAM_POSITIONS:
        enemy = enemies_by_position.get(position, {})
        column_prefix = position.lower()
        row[f"enemy_{column_prefix}_champion"] = enemy.get("champion_name", "")
        row[f"enemy_{column_prefix}_champion_mastery"] = enemy.get(
            "champion_mastery",
            0,
        )
        row[f"enemy_{column_prefix}_kda"] = enemy.get("kda", 0)

    return row


def write_features_to_csv(
    features: dict[str, Any],
    csv_path: Path = CSV_PATH,
) -> Path:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    with csv_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(build_csv_row(features))

    return csv_path


def main() -> dict[str, Any]:
    config = load_config()
    client = create_client(config)

    player_service = RiotPlayerService(config=config, client=client)
    match_stats_service = MatchStatsService(
        config=config,
        client=client,
        riot_player_service=player_service,
    )
    match_features_service = MatchFeaturesService(
        match_stats_service=match_stats_service,
    )

    processed_files = 0
    processed_matches = 0

    for file_path, data in load_match_files():
        match_ids = data.get("match_ids", [])
        if not match_ids:
            continue

        puuid = data["puuid"]
        utente_service = UtenteService(
            player=data["player"],
            match_ids=match_ids,
            match_query=data.get("match_query", {}),
            config=config,
            client=client,
        )

        for match_id in match_ids:
            match = match_stats_service.get_match(match_id)
            features = match_features_service.build_features(
                utente_service=utente_service,
                match=match,
                puuid=puuid,
                file_path=file_path,
            )
            write_features_to_csv(features)
            processed_matches += 1

        processed_files += 1

    return {
        "processed_files": processed_files,
        "processed_matches": processed_matches,
        "csv_path": CSV_PATH,
    }


if __name__ == "__main__":
    main()
