from __future__ import annotations

import json
from pathlib import Path
import sys

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

from riot_fetch.models import Utente


def main() -> None:
    player_file = sorted(DATA_DIR.glob("*.json"))[0]

    with player_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    utente = Utente(
        player=data["player"],
        match_ids=data["match_ids"],
        match_query=data["match_query"],
    )

    match_id = utente.match_ids[0]
    stats = utente.get_kda_winrate_ultime_10(match_id)

    print(f"File giocatore: {player_file.name}")
    print(f"PUUID: {utente.puuid}")
    print(f"Match riferimento: {match_id}")
    print(f"Partite usate: {stats['games_count']}")
    print(f"KDA medio ultime 10: {stats['avg_kda']}")
    print(f"Winrate ultime 10: {stats['winrate']}%")


if __name__ == "__main__":
    main()
