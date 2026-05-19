from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .giocatore import Giocatore


_POSITION_ORDER = {
    "TOP": 0,
    "JUNGLE": 1,
    "MIDDLE": 2,
    "BOTTOM": 3,
    "UTILITY": 4,
}


@dataclass
class Squadra:
    team_id: int
    win: bool
    bans: list[dict[str, Any]]
    objectives: dict[str, Any]
    feats: dict[str, Any]
    giocatori: list[Giocatore] = field(repr=False)
    data: dict[str, Any] = field(repr=False)

    @classmethod
    def from_match_data(cls,team_data: dict[str, Any],giocatori: list[dict[str, Any]]) -> Squadra:
        team_id = team_data["teamId"]
        raw_giocatori = list(giocatori)
        raw_giocatori.sort(
            key=lambda player: _POSITION_ORDER.get(player.get("teamPosition"), 99)
        )

        return cls(
            team_id=team_id,
            win=team_data.get("win", False),
            bans=team_data.get("bans", []),
            objectives=team_data.get("objectives", {}),
            feats=team_data.get("feats", {}),
            giocatori=[
                Giocatore.from_match_data(player_data)
                for player_data in raw_giocatori
            ],
            data=team_data,
        )
