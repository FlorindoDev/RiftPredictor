from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client import create_client
from ..config import RiotConfig, load_config
from .giocatore import Giocatore
from .squadra import Squadra


_PLATFORM_TO_ROUTING_REGION = {
    "BR1": "AMERICAS",
    "LA1": "AMERICAS",
    "LA2": "AMERICAS",
    "NA1": "AMERICAS",
    "EUN1": "EUROPE",
    "EUW1": "EUROPE",
    "RU": "EUROPE",
    "TR1": "EUROPE",
    "JP1": "ASIA",
    "KR": "ASIA",
    "OC1": "SEA",
    "PH2": "SEA",
    "SG2": "SEA",
    "TH2": "SEA",
    "TW2": "SEA",
    "VN2": "SEA",
}
_ROUTING_REGIONS = {"AMERICAS", "ASIA", "EUROPE", "SEA"}


class Match:
    def __init__(
        self,
        match_id: str,
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
    ) -> None:
        self.config = config or load_config()
        self.client = client or create_client(self.config)
        self.data = self.client.match.by_id(
            routing_region_for_platform(self.config.platform_region),
            match_id,
        )

        self.metadata = self.data.get("metadata", {})
        self.info = self.data.get("info", {})
        self.match_id = self.metadata.get("matchId", match_id)
        self.queue_id = self.info.get("queueId")
        self.squadre = self._build_squadre()
        self.squadra_blu = self._get_squadra(100)
        self.squadra_rossa = self._get_squadra(200)
        self.squadra_vincitrice = self._get_squadra_vincitrice()
        self.vincitore_team_id = (
            self.squadra_vincitrice.team_id if self.squadra_vincitrice else None
        )

    def _build_squadre(self) -> list[Squadra]:
        participants = self.info.get("participants", [])
        teams = self.info.get("teams", [])
        participants_by_team = self._divide_participants_by_team(participants)

        squadre = [
            Squadra.from_match_data(
                team_data,
                participants_by_team.get(team_data["teamId"], []),
            )
            for team_data in teams
        ]
        squadre.sort(key=lambda squadra: squadra.team_id)
        return squadre

    def _divide_participants_by_team(self,participants: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
        participants_by_team: dict[int, list[dict[str, Any]]] = {
            100: [],
            200: [],
        }

        for participant in participants:
            team_id = participant.get("teamId")
            if team_id in participants_by_team:
                participants_by_team[team_id].append(participant)

        return participants_by_team

    def _get_squadra(self, team_id: int) -> Squadra:
        for squadra in self.squadre:
            if squadra.team_id == team_id:
                return squadra
        raise ValueError(f"Team {team_id} not found in match {self.match_id}")

    def _get_squadra_vincitrice(self) -> Squadra | None:
        for squadra in self.squadre:
            if squadra.win:
                return squadra
        return None

    def get_giocatore_by_puuid(self, puuid: str) -> Giocatore | None:
        for squadra in self.squadre:
            for giocatore in squadra.giocatori:
                if giocatore.puuid == puuid:
                    return giocatore
        return None

    def get_player_by_lane(self, squadra: Squadra, lane: str) -> Giocatore:
        lane = lane.upper()

        for giocatore in squadra.giocatori:
            if giocatore.team_position == lane:
                return giocatore

        raise ValueError(f"Lane {lane} not found in team {squadra.team_id}")

    def get_lane_rank_difference(
        self,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any]:
        blue_player = self.get_player_by_lane(self.squadra_blu, lane)
        red_player = self.get_player_by_lane(self.squadra_rossa, lane)

        blue_rank = blue_player.get_info_player(
            queue_type=queue_type,
            config=self.config,
            client=self.client,
        )
        red_rank = red_player.get_info_player(
            queue_type=queue_type,
            config=self.config,
            client=self.client,
        )
        blue_rank_number = blue_rank["rank"] if blue_rank else 0
        red_rank_number = red_rank["rank"] if red_rank else 0

        return {
            "lane": lane.upper(),
            "blue_player": blue_player,
            "red_player": red_player,
            "blue_rank": blue_rank_number,
            "red_rank": red_rank_number,
            "rank_difference": blue_rank_number - red_rank_number,
            "blue_rank_info": blue_rank,
            "red_rank_info": red_rank,
        }


def routing_region_for_platform(platform_region: str) -> str:
    region = platform_region.upper()
    if region in _ROUTING_REGIONS:
        return region

    try:
        return _PLATFORM_TO_ROUTING_REGION[region]
    except KeyError as exc:
        raise ValueError(f"Unsupported Riot platform region: {platform_region}") from exc
