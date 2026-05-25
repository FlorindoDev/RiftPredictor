from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..client_riot.constants import routing_region_for_platform
from ..models.match import Match
from .match_stats_service import MatchStatsService


class UtenteService:
    def __init__(
        self,
        player: dict[str, Any],
        match_ids: list[str],
        match_query: dict[str, Any],
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
        match_stats_service: MatchStatsService | None = None,
    ) -> None:
        self.player = player
        self.match_ids = match_ids
        self.match_query = match_query
        self.config = config or load_config()
        self.client = client or create_client(self.config)
        self.match_stats_service = match_stats_service or MatchStatsService(
            config=self.config,
            client=self.client,
        )
        self._match_cache: dict[str, Match] = {}

    @property
    def puuid(self) -> str:
        return self.player.get("puuid", "")

    def get_kda_winrate_ultime_10(self, match_id: str) -> dict[str, Any]:
        if not self.puuid:
            raise ValueError("puuid mancante: impossibile calcolare KDA e winrate")

        previous_match_ids = self._get_previous_match_ids(
            match_id=match_id,
            count=10,
        )

        kda_values: list[float] = []
        wins = 0

        for previous_match_id in previous_match_ids:
            match = self._get_match(previous_match_id)
            giocatore = match.get_giocatore_by_puuid(self.puuid)

            if not giocatore:
                continue

            kda_values.append(giocatore.kda)
            if giocatore.win:
                wins += 1

        games_count = len(kda_values)

        return {
            "match_id": match_id,
            "match_ids": previous_match_ids,
            "games_count": games_count,
            "avg_kda": round(sum(kda_values) / games_count, 2) if games_count else 0,
            "winrate": round((wins / games_count) * 100, 2) if games_count else 0,
            "wins": wins,
            "losses": games_count - wins,
        }

    def get_kda_ultime_10(self, match_id: str) -> float:
        stats = self.get_kda_winrate_ultime_10(match_id=match_id)
        return stats["avg_kda"]

    def get_winrate_ultime_10(self, match_id: str) -> float:
        stats = self.get_kda_winrate_ultime_10(match_id=match_id)
        return stats["winrate"]

    def _get_previous_match_ids(self, match_id: str, count: int) -> list[str]:
        previous_match_ids = self._get_saved_previous_match_ids(match_id, count)

        if len(previous_match_ids) >= count:
            return previous_match_ids

        current_match = self._get_match(match_id)
        fetched_match_ids = self.client.match.matchlist_by_puuid(
            routing_region_for_platform(self.config.platform_region),
            self.puuid,
            count=count,
            queue=self.match_query.get("match_queue"),
            type=self.match_query.get("match_type"),
            end_time=self._get_match_timestamp_seconds(current_match) - 1,
        )

        for fetched_match_id in fetched_match_ids:
            if fetched_match_id not in previous_match_ids:
                previous_match_ids.append(fetched_match_id)
            if len(previous_match_ids) == count:
                break

        return previous_match_ids

    def _get_saved_previous_match_ids(self, match_id: str, count: int) -> list[str]:
        try:
            index = self.match_ids.index(match_id)
        except ValueError:
            return []

        return self.match_ids[index + 1 : index + 1 + count]

    def _get_match(self, match_id: str) -> Match:
        if match_id not in self._match_cache:
            self._match_cache[match_id] = self.match_stats_service.get_match(match_id)

        return self._match_cache[match_id]

    def _get_match_timestamp_seconds(self, match: Match) -> int:
        timestamp_ms = (
            match.info.get("gameStartTimestamp")
            or match.info.get("gameCreation")
            or match.info.get("gameEndTimestamp")
        )

        if not timestamp_ms:
            raise ValueError(f"Timestamp mancante per il match {match.match_id}")

        return int(timestamp_ms) // 1000
