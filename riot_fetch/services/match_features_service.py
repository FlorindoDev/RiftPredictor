from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

from ..models.match import Match
from ..models.squadra import Squadra
from .match_stats_service import MatchStatsService
from .utente_service import UtenteService


RECENT_MATCH_COUNT = 10


class MatchFeaturesService:
    def __init__(
        self,
        match_stats_service: MatchStatsService,
        recent_match_count: int = RECENT_MATCH_COUNT,
    ) -> None:
        self.match_stats_service = match_stats_service
        self.recent_match_count = recent_match_count

    def build_features(
        self,
        utente_service: UtenteService,
        match: Match,
        puuid: str,
        file_path: Path | None = None,
    ) -> dict[str, Any]:
        player_team = match.get_squadra_by_puuid(puuid)
        enemy_team = match.get_squadra_avversaria(player_team)
        players_recent_stats = self.build_players_recent_stats(
            utente_service=utente_service,
            match=match,
            puuid=puuid,
        )
        rank_differences = self.match_stats_service.get_lane_rank_differences(
            match,
            players_recent_stats=players_recent_stats,
            queue_type=utente_service.player["queueType"]
        )

        features = {
            "personal_features": self.build_personal_features(
                utente_service=utente_service,
                match=match,
                puuid=puuid,
                recent_stats=players_recent_stats.get(puuid),
            ),
            "team_features": self.build_team_features(
                rank_differences=rank_differences,
                team=player_team,
                include_rank_differences=True,
            ),
            "enemy_features": self.build_team_features(
                rank_differences=rank_differences,
                team=enemy_team,
            ),
        }

        if file_path is not None:
            features["file_path"] = file_path

        return features

    def build_players_recent_stats(
        self,
        utente_service: UtenteService,
        match: Match,
        puuid: str,
    ) -> dict[str, dict[str, Any]]:
        players_recent_stats = {}

        for squadra in match.squadre:
            for player in squadra.giocatori:
                player_utente_service = utente_service
                if player.puuid != puuid:
                    player_utente_service = UtenteService(
                        player={"puuid": player.puuid},
                        match_ids=[],
                        match_query=utente_service.match_query,
                        config=utente_service.config,
                        client=utente_service.client,
                        match_stats_service=utente_service.match_stats_service,
                    )

                players_recent_stats[player.puuid] = (
                    player_utente_service.get_kda_winrate_ultime_10(match.match_id)
                )

        return players_recent_stats

    def build_team_features(
        self,
        rank_differences: list[dict[str, Any]],
        team: Squadra,
        include_rank_differences: bool = False,
    ) -> dict[str, Any]:
        team_player_key = (
            "blue_players_info" if team.team_id == 100 else "red_players_info"
        )
        team_recent_stats = self._get_recent_stats_by_player_key(
            rank_differences,
            team_player_key,
        )
        team_winrates = [
            recent_stats["winrate"] for recent_stats in team_recent_stats
        ]
        team_kdas = [
            recent_stats["avg_kda"] for recent_stats in team_recent_stats
        ]

        avg_team_winrate = round(mean(team_winrates), 2) if team_winrates else 0
        avg_team_kda = round(mean(team_kdas), 2) if team_kdas else 0
        composition = self.match_stats_service.riot_player_service.get_team_composition(
            team
        )
        team_players_info_by_lane = self._get_team_players_info_by_lane(
            rank_differences,
            team_player_key,
        )

        for player_features in composition:
            player_info = team_players_info_by_lane.get(
                player_features["team_position"].upper()
            )
            if player_info is None:
                continue

            player_features["kda"] = player_info.get("avg_kda", 0)
            player_features["winrate"] = player_info.get("winrate", 0)

        features = {
            "win": team.win,
            "avg_winrate": avg_team_winrate,
            "avg_kda": avg_team_kda,
            "composition": composition,
        }

        if not include_rank_differences:
            return features

        if not rank_differences:
            features.update(
                {
                    "avg_player_team_minus_enemy": None,
                    "avg_blue_minus_red": None,
                    "rank_differences": [],
                }
            )
            return features

        avg_blue_minus_red = mean(
            rank_difference["rank_difference"]
            for rank_difference in rank_differences
        )
        avg_player_team_minus_enemy = (
            avg_blue_minus_red if team.team_id == 100 else -avg_blue_minus_red
        )
        features.update(
            {
                "avg_player_team_minus_enemy": round(avg_player_team_minus_enemy, 2),
                "avg_blue_minus_red": round(avg_blue_minus_red, 2),
                "rank_differences": rank_differences,
            }
        )

        return features

    def _get_team_players_info_by_lane(
        self,
        rank_differences: list[dict[str, Any]],
        player_key: str,
    ) -> dict[str, dict[str, Any]]:
        team_players_info_by_lane = {}
        for rank_difference in rank_differences:
            player_info = rank_difference[player_key]
            if player_info is not None:
                team_players_info_by_lane[rank_difference["lane"]] = player_info

        return team_players_info_by_lane

    def _get_recent_stats_by_player_key(
        self,
        rank_differences: list[dict[str, Any]],
        player_key: str,
    ) -> list[dict[str, Any]]:
        recent_stats_by_player = []
        for rank_difference in rank_differences:
            player_info = rank_difference[player_key]
            if player_info is None:
                continue

            recent_stats = player_info.get("recent_stats")
            if recent_stats is not None:
                recent_stats_by_player.append(recent_stats)

        return recent_stats_by_player

    def build_personal_features(
        self,
        utente_service: UtenteService,
        match: Match,
        puuid: str,
        recent_stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        player = match.get_giocatore_by_puuid(puuid)
        if not player:
            raise ValueError(f"Giocatore {puuid} non trovato nel match {match.match_id}")

        if recent_stats is None:
            recent_stats = utente_service.get_kda_winrate_ultime_10(match.match_id)

        return {
            "match_id": match.match_id,
            "puuid": puuid,
            "player": player,
            "champion_id": player.champion_id,
            "recent_match_count": self.recent_match_count,
            "recent_stats": recent_stats,
        }
