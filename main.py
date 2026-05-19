from __future__ import annotations

import argparse
from typing import Any

from riotwatcher import ApiError

from riot_fetch.models import Match, Squadra


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test veloce dei model Riot usando un match id.",
    )
    parser.add_argument(
        "match_id",
        nargs="?",
        help="Match id Riot, esempio: EUW1_7858526611",
    )
    return parser.parse_args()


def get_match_id(match_id_arg: str | None) -> str:
    match_id = match_id_arg or input("Inserisci match id: ")
    match_id = match_id.strip()

    if not match_id:
        raise ValueError("Devi inserire un match id, esempio: EUW1_7858526611")

    return match_id


def objective_kills(objectives: dict[str, Any], objective_name: str) -> int:
    objective = objectives.get(objective_name, {})
    return int(objective.get("kills", 0))


def format_bans(squadra: Squadra) -> str:
    champion_ids = [
        ban.get("championId")
        for ban in squadra.bans
        if ban.get("championId", -1) != -1
    ]
    return ", ".join(str(champion_id) for champion_id in champion_ids) or "nessun ban"


def print_squadra(squadra: Squadra, nome: str) -> None:
    risultato = "WIN" if squadra.win else "LOSS"
    baron = objective_kills(squadra.objectives, "baron")
    dragon = objective_kills(squadra.objectives, "dragon")
    tower = objective_kills(squadra.objectives, "tower")

    print(f"\n{nome} - team_id={squadra.team_id} - {risultato}")
    print(f"Ban: {format_bans(squadra)}")
    print(f"Obiettivi: baron={baron}, dragon={dragon}, tower={tower}")

    for giocatore in squadra.giocatori:
        nome_giocatore = (
            giocatore.riot_id_game_name
            or giocatore.summoner_name
            or giocatore.puuid[:8]
            or "sconosciuto"
        )
        posizione = giocatore.team_position or giocatore.individual_position or "-"
        kda = f"{giocatore.kills}/{giocatore.deaths}/{giocatore.assists}"

        print(
            f"  {posizione:<7} "
            f"{nome_giocatore:<18} "
            f"{giocatore.champion_name:<14} "
            f"KDA {kda}"
        )


def print_match(match: Match) -> None:
    vincitore = (
        match.squadra_vincitrice.team_id
        if match.squadra_vincitrice is not None
        else "non trovato"
    )

    print(f"\nMatch: {match.match_id}")
    print(f"Queue id: {match.queue_id}")
    print(f"Team vincitore: {vincitore}")
    print(f"Numero squadre create: {len(match.squadre)}")

    print_squadra(match.squadra_blu, "Squadra blu")
    print_squadra(match.squadra_rossa, "Squadra rossa")


def main() -> None:
    args = parse_args()

    try:
        match_id = get_match_id(args.match_id)
        match = Match(match_id)
    except ApiError as exc:
        print(f"Errore Riot API: {exc}")
        return
    except ValueError as exc:
        print(f"Errore: {exc}")
        return

    print_match(match)


if __name__ == "__main__":
    main()
