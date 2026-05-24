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
        composition = self.riot_player_service.get_team_composition(team)
        player_info_by_lane = self._get_player_info_by_lane(
            rank_differences,
            team_player_key,
        )
        for player_features in composition:
            player_info = player_info_by_lane.get(
                player_features["team_position"].upper()
            )
            if player_info is None:
                continue

            player_features["kda"] = player_info.get("avg_kda", 0)
            player_features["winrate"] = player_info.get("winrate", 0)

        features = {
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

    def _get_player_info_by_lane(
        self,
        rank_differences: list[dict[str, Any]],
        player_key: str,
    ) -> dict[str, dict[str, Any]]:
        player_info_by_lane = {}
        for rank_difference in rank_differences:
            player_info = rank_difference[player_key]
            if player_info is not None:
                player_info_by_lane[rank_difference["lane"]] = player_info

        return player_info_by_lane

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
