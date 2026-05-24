from __future__ import annotations

from statistics import mean
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

    def build_team_features(
        self,
        rank_differences: list[dict[str, Any]],
        team: Squadra,
        include_rank_differences: bool = False,
    ) -> dict[str, Any]:
        team_rank_key = "blue_rank_info" if team.team_id == 100 else "red_rank_info"
        team_winrates = self._get_winrates_by_rank_key(
            rank_differences,
            team_rank_key,
        )
        avg_team_winrate = round(mean(team_winrates), 2) if team_winrates else 0
        features = {
            "avg_winrate": avg_team_winrate,
            "composition": self.riot_player_service.get_team_composition(team),
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

    def _get_winrates_by_rank_key(
        self,
        rank_differences: list[dict[str, Any]],
        rank_key: str,
    ) -> list[float]:
        winrates = []
        for rank_difference in rank_differences:
            rank_info = rank_difference[rank_key]
            if rank_info is not None:
                winrates.append(rank_info["winrate"])

        return winrates
