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
    "match_id",
    "puuid",
    "avg_rank_difference_player_team_vs_enemy",
    "avg_player_team_winrate",
    "avg_enemy_winrate",
    "ally_ranked_count",
    "ally_rank_missing_count",
    "enemy_ranked_count",
    "enemy_rank_missing_count",
    "ally_top_champion_id",
    "ally_top_kda",
    "ally_jungle_champion_id",
    "ally_jungle_kda",
    "ally_middle_champion_id",
    "ally_middle_kda",
    "ally_bottom_champion_id",
    "ally_bottom_kda",
    "ally_utility_champion_id",
    "ally_utility_kda",
    "enemy_top_champion_id",
    "enemy_top_kda",
    "enemy_jungle_champion_id",
    "enemy_jungle_kda",
    "enemy_middle_champion_id",
    "enemy_middle_kda",
    "enemy_bottom_champion_id",
    "enemy_bottom_kda",
    "enemy_utility_champion_id",
    "enemy_utility_kda",
    "target",
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
        "match_id": personal_features["match_id"],
        "puuid": personal_features["puuid"],
        "avg_rank_difference_player_team_vs_enemy": team_features[
            "avg_player_team_minus_enemy"
        ],
        "avg_player_team_winrate": team_features["avg_winrate"],
        "avg_enemy_winrate": enemy_features["avg_winrate"],
        "ally_ranked_count": team_features["ranked_count"],
        "ally_rank_missing_count": team_features["rank_missing_count"],
        "enemy_ranked_count": enemy_features["ranked_count"],
        "enemy_rank_missing_count": enemy_features["rank_missing_count"],
        "target": team_features["win"],
    }

    allies_by_position = {
        ally["team_position"].upper(): ally
        for ally in team_features["composition"]
    }
    for position in TEAM_POSITIONS:
        ally = allies_by_position.get(position, {})
        column_prefix = position.lower()
        row[f"ally_{column_prefix}_champion_id"] = ally.get("champion_id", 0)
        row[f"ally_{column_prefix}_kda"] = ally.get("kda", 0)

    enemies_by_position = {
        enemy["team_position"].upper(): enemy
        for enemy in enemy_features["composition"]
    }
    for position in TEAM_POSITIONS:
        enemy = enemies_by_position.get(position, {})
        column_prefix = position.lower()
        row[f"enemy_{column_prefix}_champion_id"] = enemy.get("champion_id", 0)
        row[f"enemy_{column_prefix}_kda"] = enemy.get("kda", 0)

    return row


def write_features_to_csv(
    features: dict[str, Any],
    csv_path: Path = CSV_PATH,
) -> Path:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    if not write_header:
        with csv_path.open("r", encoding="utf-8", newline="") as file:
            existing_header = next(csv.reader(file), [])
        if existing_header != CSV_FIELDNAMES:
            raise ValueError(
                f"Schema CSV esistente non compatibile con le feature attuali: "
                f"{csv_path}"
            )

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
    skipped_files = 0
    skipped_matches = 0

    for file_path, data in load_match_files():
        try:
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
                match_stats_service=match_stats_service,
            )
        except (KeyError, TypeError) as exc:
            skipped_files += 1
            print(f"Skip file {file_path}: dati mancanti o invalidi ({exc})")
            continue

        for match_id in match_ids:
            try:
                match = match_stats_service.get_match(match_id)
                features = match_features_service.build_features(
                    utente_service=utente_service,
                    match=match,
                    puuid=puuid,
                    file_path=file_path,
                )
            except (KeyError, TypeError, ValueError) as exc:
                skipped_matches += 1
                print(f"Skip match {match_id}: dati mancanti o invalidi ({exc})")
                continue

            try:
                write_features_to_csv(features)
            except (KeyError, TypeError) as exc:
                skipped_matches += 1
                print(f"Skip match {match_id}: feature incomplete ({exc})")
                continue

            processed_matches += 1

        processed_files += 1

    return {
        "processed_files": processed_files,
        "processed_matches": processed_matches,
        "skipped_files": skipped_files,
        "skipped_matches": skipped_matches,
        "csv_path": CSV_PATH,
    }


if __name__ == "__main__":
    main()
