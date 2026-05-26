from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "data" / "match_features.csv"
TEAM_POSITIONS = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")


def build_lane_rank_fieldnames() -> list[str]:
    fieldnames = []
    for position in TEAM_POSITIONS:
        column_prefix = position.lower()
        fieldnames.extend(
            [
                f"ally_{column_prefix}_rank_score",
                f"enemy_{column_prefix}_rank_score",
                f"{column_prefix}_rank_difference_player_team_vs_enemy",
            ]
        )

    return fieldnames


LANE_RANK_FIELDNAMES = build_lane_rank_fieldnames()

CSV_FIELDNAMES = [
    "match_id",
    "puuid",
    "avg_rank_difference_player_team_vs_enemy",
    *LANE_RANK_FIELDNAMES,
    "avg_player_team_winrate",
    "avg_enemy_winrate",
    "ally_ranked_count",
    "ally_rank_missing_count",
    "enemy_ranked_count",
    "enemy_rank_missing_count",
    "ally_top_champion_id",
    "ally_top_kda",
    "ally_top_winrate",
    "ally_jungle_champion_id",
    "ally_jungle_kda",
    "ally_jungle_winrate",
    "ally_middle_champion_id",
    "ally_middle_kda",
    "ally_middle_winrate",
    "ally_bottom_champion_id",
    "ally_bottom_kda",
    "ally_bottom_winrate",
    "ally_utility_champion_id",
    "ally_utility_kda",
    "ally_utility_winrate",
    "enemy_top_champion_id",
    "enemy_top_kda",
    "enemy_top_winrate",
    "enemy_jungle_champion_id",
    "enemy_jungle_kda",
    "enemy_jungle_winrate",
    "enemy_middle_champion_id",
    "enemy_middle_kda",
    "enemy_middle_winrate",
    "enemy_bottom_champion_id",
    "enemy_bottom_kda",
    "enemy_bottom_winrate",
    "enemy_utility_champion_id",
    "enemy_utility_kda",
    "enemy_utility_winrate",
    "target",
]


def add_lane_rank_features(
    row: dict[str, Any],
    team_features: dict[str, Any],
) -> None:
    ally_rank_key = "blue_rank" if team_features["team_id"] == 100 else "red_rank"
    enemy_rank_key = "red_rank" if team_features["team_id"] == 100 else "blue_rank"
    rank_differences_by_lane = {
        rank_difference["lane"].upper(): rank_difference
        for rank_difference in team_features.get("rank_differences", [])
    }

    for position in TEAM_POSITIONS:
        column_prefix = position.lower()
        rank_difference = rank_differences_by_lane.get(position, {})
        ally_rank = rank_difference.get(ally_rank_key)
        enemy_rank = rank_difference.get(enemy_rank_key)
        lane_rank_difference = None

        if ally_rank is not None and enemy_rank is not None:
            lane_rank_difference = round(ally_rank - enemy_rank, 2)

        row[f"ally_{column_prefix}_rank_score"] = ally_rank
        row[f"enemy_{column_prefix}_rank_score"] = enemy_rank
        row[
            f"{column_prefix}_rank_difference_player_team_vs_enemy"
        ] = lane_rank_difference


def add_composition_features(
    row: dict[str, Any],
    side: str,
    composition: list[dict[str, Any]],
) -> None:
    players_by_position = {
        player["team_position"].upper(): player
        for player in composition
    }

    for position in TEAM_POSITIONS:
        player = players_by_position.get(position, {})
        column_prefix = f"{side}_{position.lower()}"
        row[f"{column_prefix}_champion_id"] = player.get("champion_id", 0)
        row[f"{column_prefix}_kda"] = player.get("kda", 0)
        row[f"{column_prefix}_winrate"] = player.get("winrate", 0)


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

    add_lane_rank_features(row, team_features)
    add_composition_features(row, "ally", team_features["composition"])
    add_composition_features(row, "enemy", enemy_features["composition"])

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
