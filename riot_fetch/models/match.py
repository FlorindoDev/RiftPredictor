from __future__ import annotations

from typing import Any

from .giocatore import Giocatore
from .squadra import Squadra


class Match:
    def __init__(
        self,
        data: dict[str, Any],
        match_id: str | None = None,
    ) -> None:
        self.data = data
        self.metadata = self.data.get("metadata", {})
        self.info = self.data.get("info", {})
        self.match_id = self.metadata.get("matchId", match_id or "")
        self.queue_id = self.info.get("queueId")
        self.squadre = self._build_squadre()
        self.squadra_blu = self._get_squadra(100)
        self.squadra_rossa = self._get_squadra(200)
        self.squadra_vincitrice = self._get_squadra_vincitrice()
        self.vincitore_team_id = (
            self.squadra_vincitrice.team_id if self.squadra_vincitrice else None
        )

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        match_id: str | None = None,
    ) -> Match:
        return cls(data=data, match_id=match_id)

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


    #####################################################
    #                   Metodi publici                  #
    #####################################################

    
    def get_squadra_vincitrice(self) -> Squadra | None:
        return self.squadra_vincitrice

    def get_giocatore_by_puuid(self, puuid: str) -> Giocatore | None:
        for squadra in self.squadre:
            for giocatore in squadra.giocatori:
                if giocatore.puuid == puuid:
                    return giocatore
        return None

    def get_squadra_by_puuid(self, puuid: str) -> Squadra:
        for squadra in self.squadre:
            if squadra.get_giocatore_by_puuid(puuid):
                return squadra

        raise ValueError(f"Giocatore {puuid} non trovato nel match {self.match_id}")

    def get_squadra_avversaria(self, squadra: Squadra) -> Squadra:
        for match_team in self.squadre:
            if match_team.team_id != squadra.team_id:
                return match_team

        raise ValueError(f"Team avversario non trovato nel match {self.match_id}")
