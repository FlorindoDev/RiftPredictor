from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..models.match import Match
from ..models.squadra import Squadra
from .riot_player_service import RiotPlayerService


DEFAULT_LANES = ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")


class MatchStatsService:
    def __init__(
        self,
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
        riot_player_service: RiotPlayerService | None = None,
    ) -> None:
        self.config = config or load_config()
        self.client = client or create_client(self.config)
        self.riot_player_service = riot_player_service or RiotPlayerService(
            config=self.config,
            client=self.client,
        )

    def get_match(self, match_id: str) -> Match:
        return Match(match_id=match_id, config=self.config, client=self.client)

    def get_rank_player_by_lane(
        self,
        squadra: Squadra,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
        players_recent_stats: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        player = squadra.get_player_by_lane(lane)
        ranked_info = self.riot_player_service.get_info_player(
            player,
            queue_type=queue_type,
        )
        recent_stats = None
        if players_recent_stats is not None:
            recent_stats = players_recent_stats.get(player.puuid)
        player_info = self._build_player_info(ranked_info, recent_stats)

        return {
            "lane": lane.upper(),
            "player": player,
            "rank": ranked_info["rank"] if ranked_info else 0,
            "player_info": player_info,
        }

    def get_lane_rank_difference(
        self,
        match: Match,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
        players_recent_stats: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        blue_rank = self.get_rank_player_by_lane(
            squadra=match.squadra_blu,
            lane=lane,
            queue_type=queue_type,
            players_recent_stats=players_recent_stats,
        )
        red_rank = self.get_rank_player_by_lane(
            squadra=match.squadra_rossa,
            lane=lane,
            queue_type=queue_type,
            players_recent_stats=players_recent_stats,
        )

        return {
            "lane": lane.upper(),
            "blue_player": blue_rank["player"],
            "red_player": red_rank["player"],
            "blue_rank": blue_rank["rank"],
            "red_rank": red_rank["rank"],
            "rank_difference": blue_rank["rank"] - red_rank["rank"],
            "blue_players_info": blue_rank["player_info"],
            "red_players_info": red_rank["player_info"],
        }

    def get_lane_rank_differences(
        self,
        match: Match,
        lanes: tuple[str, ...] = DEFAULT_LANES,
        queue_type: str = "RANKED_SOLO_5x5",
        players_recent_stats: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self.get_lane_rank_difference(
                match=match,
                lane=lane,
                queue_type=queue_type,
                players_recent_stats=players_recent_stats,
            )
            for lane in lanes
        ]

    def _build_player_info(
        self,
        ranked_info: dict[str, Any] | None,
        recent_stats: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if ranked_info is None and recent_stats is None:
            return None

        player_info = dict(ranked_info) if ranked_info else {}
        if recent_stats is not None:
            player_info.update(
                {
                    "recent_stats": recent_stats,
                    "avg_kda": recent_stats["avg_kda"],
                    "winrate": recent_stats["winrate"],
                    "recent_winrate": recent_stats["winrate"],
                }
            )

        return player_info
