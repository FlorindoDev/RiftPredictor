from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..client_riot.constants import routing_region_for_platform
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
        self._match_cache: dict[str, Match] = {}

    def get_match(self, match_id: str) -> Match:
        if match_id not in self._match_cache:
            match_data = self.client.match.by_id(
                routing_region_for_platform(self.config.platform_region),
                match_id,
            )
            self._match_cache[match_id] = Match.from_data(
                data=match_data,
                match_id=match_id,
            )

        return self._match_cache[match_id]

    def get_rank_player_by_lane(
        self,
        squadra: Squadra,
        lane: str,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any]:
        player = squadra.get_player_by_lane(lane)
        ranked_info = self.riot_player_service.get_info_player(
            player,
            queue_type=queue_type,
        )
        rank_score = ranked_info["rank_score"] if ranked_info else None

        return {
            "lane": lane.upper(),
            "player": player,
            "rank": rank_score,
            "rank_missing": rank_score is None,
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

        rank_difference = None
        if blue_rank["rank"] is not None and red_rank["rank"] is not None:
            rank_difference = round(blue_rank["rank"] - red_rank["rank"], 2)

        return {
            "lane": lane.upper(),
            "blue_rank": blue_rank["rank"],
            "red_rank": red_rank["rank"],
            "rank_difference": rank_difference,
        }

    def get_lane_rank_differences(
        self,
        match: Match,
        lanes: tuple[str, ...] = DEFAULT_LANES,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> list[dict[str, Any]]:
        return [
            self.get_lane_rank_difference(
                match=match,
                lane=lane,
                queue_type=queue_type,
            )
            for lane in lanes
        ]
