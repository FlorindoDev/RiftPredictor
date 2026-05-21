from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig
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

    def get_giocatore_by_puuid(self, puuid: str) -> Giocatore | None:
        for giocatore in self.giocatori:
            if giocatore.puuid == puuid:
                return giocatore
        return None

    def get_player_by_lane(self, lane: str) -> Giocatore:
        lane = lane.upper()

        for giocatore in self.giocatori:
            if giocatore.team_position == lane:
                return giocatore

        raise ValueError(f"Lane {lane} not found in team {self.team_id}")

    def get_rank_player_by_lane(
        self,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
    ) -> dict[str, Any]:
        player = self.get_player_by_lane(lane)
        rank_info = player.get_info_player(
            queue_type=queue_type,
            config=config,
            client=client,
        )

        return {
            "lane": lane.upper(),
            "player": player,
            "rank": rank_info["rank"] if rank_info else 0,
            "rank_info": rank_info,
        }
