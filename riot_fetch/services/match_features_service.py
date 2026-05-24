from __future__ import annotations

from pathlib import Path
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
        rank_differences: list[dict[str, Any]],
        player_team: Squadra,
        enemy_team: Squadra,
        file_path: Path | None = None,
    ) -> dict[str, Any]:
        features = {
            "personal_features": self.build_personal_features(
                utente_service=utente_service,
                match=match,
                puuid=puuid,
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

    def build_personal_features(
        self,
        utente_service: UtenteService,
        match: Match,
        puuid: str,
    ) -> dict[str, Any]:
        player = match.get_giocatore_by_puuid(puuid)
        if not player:
            raise ValueError(f"Giocatore {puuid} non trovato nel match {match.match_id}")

        recent_stats = utente_service.get_kda_winrate_ultime_10(match.match_id)

        return {
            "player": player,
            "champion_name": player.champion_name,
            "recent_match_count": self.recent_match_count,
            "recent_stats": recent_stats,
        }
