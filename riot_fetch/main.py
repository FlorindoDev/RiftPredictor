from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from riot_fetch.client_riot import create_client, load_config
from riot_fetch.services.match_features_csv_writer import (
    CSV_PATH,
    write_features_to_csv,
)
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


def load_match_files() -> list[tuple[Path, dict[str, Any]]]:
    json_files = sorted(DATA_DIR.rglob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"Nessun file JSON trovato in {DATA_DIR}")

    files = []
    for file_path in json_files:
        with file_path.open("r", encoding="utf-8") as file:
            files.append((file_path, json.load(file)))

    return files


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
                print(features)
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
