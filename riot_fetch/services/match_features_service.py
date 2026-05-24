from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.match import Match
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
        )

        features = {
            "personal_features": self.build_personal_features(
                utente_service=utente_service,
                match=match,
                puuid=puuid,
                recent_stats=players_recent_stats.get(puuid),
            ),
            "team_features": self.match_stats_service.build_team_features(
                rank_differences=rank_differences,
                team=player_team,
                include_rank_differences=True,
            ),
            "enemy_features": self.match_stats_service.build_team_features(
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
                    )

                players_recent_stats[player.puuid] = (
                    player_utente_service.get_kda_winrate_ultime_10(match.match_id)
                )

        return players_recent_stats

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
            "player": player,
            "champion_name": player.champion_name,
            "recent_match_count": self.recent_match_count,
            "recent_stats": recent_stats,
        }
