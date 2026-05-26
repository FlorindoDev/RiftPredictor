from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

from ..models.match import Match
from ..models.squadra import Squadra
from .match_stats_service import MatchStatsService
from .utente_service import UtenteService

# TODO: riffallo bene

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
            queue_type=utente_service.player["queueType"],
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
                players_recent_stats=players_recent_stats,
                include_rank_differences=True,
            ),
            "enemy_features": self.build_team_features(
                rank_differences=rank_differences,
                team=enemy_team,
                players_recent_stats=players_recent_stats,
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
        players_recent_stats: dict[str, dict[str, Any]],
        include_rank_differences: bool = False,
    ) -> dict[str, Any]:
        features = self._build_base_team_features(
            rank_differences=rank_differences,
            team=team,
            players_recent_stats=players_recent_stats,
        )

        if include_rank_differences:
            features.update(
                self._build_rank_difference_features(
                    team_id=team.team_id,
                    rank_differences=rank_differences,
                )
            )

        return features

    def _build_base_team_features(
        self,
        rank_differences: list[dict[str, Any]],
        team: Squadra,
        players_recent_stats: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        ranked_count, rank_missing_count = self._get_team_rank_counts(
            team=team,
            rank_differences=rank_differences,
        )
        avg_team_winrate, avg_team_kda = self._get_team_recent_averages(
            team=team,
            players_recent_stats=players_recent_stats,
        )

        return {
            "team_id": team.team_id,
            "win": team.win,
            "avg_winrate": avg_team_winrate,
            "avg_kda": avg_team_kda,
            "ranked_count": ranked_count,
            "rank_missing_count": rank_missing_count,
            "composition": self._build_team_composition(
                team=team,
                players_recent_stats=players_recent_stats,
            ),
        }

    def _get_team_rank_counts(
        self,
        team: Squadra,
        rank_differences: list[dict[str, Any]],
    ) -> tuple[int, int]:
        team_rank_key = "blue_rank" if team.team_id == 100 else "red_rank"
        ranked_count = sum(
            1
            for rank_difference in rank_differences
            if rank_difference[team_rank_key] is not None
        )

        return ranked_count, len(rank_differences) - ranked_count

    def _get_team_recent_averages(
        self,
        team: Squadra,
        players_recent_stats: dict[str, dict[str, Any]],
    ) -> tuple[float, float]:
        team_recent_stats = self._get_recent_stats_for_team(
            team=team,
            players_recent_stats=players_recent_stats,
        )

        return (
            self._average_recent_stat(team_recent_stats, "winrate"),
            self._average_recent_stat(team_recent_stats, "avg_kda"),
        )

    @staticmethod
    def _average_recent_stat(
        team_recent_stats: list[dict[str, Any]],
        stat_name: str,
    ) -> float:
        stat_values = [recent_stats[stat_name] for recent_stats in team_recent_stats]
        return round(mean(stat_values), 2) if stat_values else 0

    def _build_team_composition(
        self,
        team: Squadra,
        players_recent_stats: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        recent_stats_by_lane = self._get_recent_stats_by_lane(
            team=team,
            players_recent_stats=players_recent_stats,
        )
        composition = self.match_stats_service.riot_player_service.get_team_composition(
            team
        )

        return [
            self._add_recent_stats_to_player_features(
                player_features=player_features,
                recent_stats_by_lane=recent_stats_by_lane,
            )
            for player_features in composition
        ]

    def _get_recent_stats_by_lane(
        self,
        team: Squadra,
        players_recent_stats: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any] | None]:
        return {
            player.team_position.upper(): players_recent_stats.get(player.puuid)
            for player in team.giocatori
        }

    @staticmethod
    def _add_recent_stats_to_player_features(
        player_features: dict[str, Any],
        recent_stats_by_lane: dict[str, dict[str, Any] | None],
    ) -> dict[str, Any]:
        recent_stats = recent_stats_by_lane.get(
            player_features["team_position"].upper()
        )
        if recent_stats is None:
            return player_features

        return {
            **player_features,
            "kda": recent_stats.get("avg_kda", 0),
            "winrate": recent_stats.get("winrate", 0),
        }

    @staticmethod
    def _build_rank_difference_features(
        team_id: int,
        rank_differences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        
        
        valid_rank_differences = [
            rank_difference["rank_difference"]
            for rank_difference in rank_differences
            if rank_difference["rank_difference"] is not None
        ]

        if not valid_rank_differences:
            return {
                "avg_player_team_minus_enemy": None,
                "avg_blue_minus_red": None,
                "rank_comparison_count": 0,
                "rank_differences": rank_differences,
            }

        avg_blue_minus_red = mean(valid_rank_differences)
        avg_player_team_minus_enemy = (
            avg_blue_minus_red if team_id == 100 else -avg_blue_minus_red
        )

        return {
            "avg_player_team_minus_enemy": round(avg_player_team_minus_enemy, 2),
            "avg_blue_minus_red": round(avg_blue_minus_red, 2),
            "rank_comparison_count": len(valid_rank_differences),
            "rank_differences": rank_differences,
        }

    def _get_recent_stats_for_team(
        self,
        team: Squadra,
        players_recent_stats: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            recent_stats
            for player in team.giocatori
            if (recent_stats := players_recent_stats.get(player.puuid)) is not None
        ]

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
