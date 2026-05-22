from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..models.match import Match
from ..models.squadra import Squadra
from .riot_player_service import RiotPlayerService


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

    def get_rank_player_by_lane(
        self,
        squadra: Squadra,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any]:
        player = squadra.get_player_by_lane(lane)
        rank_info = self.riot_player_service.get_info_player(
            player,
            queue_type=queue_type,
        )

        return {
            "lane": lane.upper(),
            "player": player,
            "rank": rank_info["rank"] if rank_info else 0,
            "rank_info": rank_info,
        }

    def get_lane_rank_difference(
        self,
        match: Match,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any]:
        blue_rank = self.get_rank_player_by_lane(
            squadra=match.squadra_blu,
            lane=lane,
            queue_type=queue_type,
        )
        red_rank = self.get_rank_player_by_lane(
            squadra=match.squadra_rossa,
            lane=lane,
            queue_type=queue_type,
        )

        return {
            "lane": lane.upper(),
            "blue_player": blue_rank["player"],
            "red_player": red_rank["player"],
            "blue_rank": blue_rank["rank"],
            "red_rank": red_rank["rank"],
            "rank_difference": blue_rank["rank"] - red_rank["rank"],
            "blue_rank_info": blue_rank["rank_info"],
            "red_rank_info": red_rank["rank_info"],
        }
