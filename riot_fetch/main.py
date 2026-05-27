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


def load_csv_resume_point(csv_path: Path = CSV_PATH) -> dict[str, str] | None:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            return None

        missing_columns = {"match_id", "puuid"} - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Colonne mancanti nel CSV {csv_path}: {missing}")

        last_row = None
        for row in reader:
            if row.get("match_id") and row.get("puuid"):
                last_row = row

    if last_row is None:
        return None

    return {
        "match_id": last_row["match_id"],
        "puuid": last_row["puuid"],
    }


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
    resume_skipped_files = 0
    resume_skipped_matches = 0

    resume_point = load_csv_resume_point()
    resume_found = resume_point is None
    if resume_point is not None:
        print(
            "Ripresa CSV da "
            f"puuid={resume_point['puuid']} match_id={resume_point['match_id']}"
        )

    for file_path, data in load_match_files():
        try:
            match_ids = data.get("match_ids", [])
            if not match_ids:
                continue

            puuid = data["puuid"]
            player = data["player"]
            match_query = data.get("match_query", {})
        except (KeyError, TypeError) as exc:
            skipped_files += 1
            print(f"Skip file {file_path}: dati mancanti o invalidi ({exc})")
            continue

        start_match_index = 0
        if not resume_found:
            if puuid != resume_point["puuid"]:
                resume_skipped_files += 1
                continue

            resume_found = True
            try:
                start_match_index = match_ids.index(resume_point["match_id"]) + 1
            except ValueError as exc:
                raise ValueError(
                    "Match dell'ultima riga CSV non trovato nel file del player "
                    f"{file_path}: {resume_point['match_id']}"
                ) from exc

            resume_skipped_matches += start_match_index
            print(
                f"Riparto da {file_path}: "
                f"saltati {start_match_index} match gia' scritti."
            )

        if start_match_index >= len(match_ids):
            continue

        try:
            utente_service = UtenteService(
                player=player,
                match_ids=match_ids,
                match_query=match_query,
                config=config,
                client=client,
                match_stats_service=match_stats_service,
            )
        except (KeyError, TypeError) as exc:
            skipped_files += 1
            print(f"Skip file {file_path}: dati mancanti o invalidi ({exc})")
            continue

        for match_id in match_ids[start_match_index:]:
            try:
                match = match_stats_service.get_match(match_id)
                features = match_features_service.build_features(
                    utente_service=utente_service,
                    match=match,
                    puuid=puuid,
                    file_path=file_path,
                )
                print(json.dumps(features, indent=2, ensure_ascii=False))
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

    if not resume_found:
        raise ValueError(
            "Player dell'ultima riga CSV non trovato nei file sorgente: "
            f"{resume_point['puuid']}"
        )

    return {
        "processed_files": processed_files,
        "processed_matches": processed_matches,
        "skipped_files": skipped_files,
        "skipped_matches": skipped_matches,
        "resume_skipped_files": resume_skipped_files,
        "resume_skipped_matches": resume_skipped_matches,
        "csv_path": CSV_PATH,
    }


if __name__ == "__main__":
    main()
