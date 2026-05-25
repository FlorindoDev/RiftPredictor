from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..client_riot.constants import (
    APEX_TIER_BASE_SCORE,
    RANK_DIVISIONI,
    RANK_TIERS,
    TIER_SENZA_DIVISIONE,
)
from ..models.giocatore import Giocatore
from ..models.squadra import Squadra


def rank_score_for_entry(
    tier: str,
    divisione: str,
    league_points: Any,
) -> float | None:
    try:
        league_points_value = int(league_points)
    except (TypeError, ValueError):
        league_points_value = 0

    if tier in APEX_TIER_BASE_SCORE:
        return round(APEX_TIER_BASE_SCORE[tier] + (league_points_value / 100), 2)

    tier_numero = RANK_TIERS.get(tier, 0)
    divisione_numero = RANK_DIVISIONI.get(divisione, 0)
    if not tier_numero or not divisione_numero:
        return None

    base_score = ((tier_numero - 1) * 4) + (5 - divisione_numero)
    return round(base_score + (league_points_value / 100), 2)


class RiotPlayerService:
    def __init__(
        self,
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
    ) -> None:
        self.config = config or load_config()
        self.client = client or create_client(self.config)

    def get_champion(self, giocatore: Giocatore) -> dict[str, Any]:
        if not giocatore.puuid:
            raise ValueError("puuid mancante: impossibile leggere la champion mastery")
        if not giocatore.champion_id:
            raise ValueError(
                "champion_id mancante: impossibile leggere la champion mastery"
            )

        mastery = self.client.champion_mastery.by_puuid_by_champion(
            self.config.platform_region,
            giocatore.puuid,
            giocatore.champion_id,
        )

        return {
            "champion_id": giocatore.champion_id,
            "champion_name": giocatore.champion_name,
            "mastery": mastery,
        }

    def get_team_composition(self, squadra: Squadra) -> list[dict[str, Any]]:
        composition = []
        for giocatore in squadra.giocatori:
            composition.append(
                {
                    "team_position": giocatore.team_position,
                    "champion_id": giocatore.champion_id,
                    "role": giocatore.role,
                }
            )

        return composition

    def get_info_player(
        self,
        giocatore: Giocatore,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any] | None:
        ranked_entries = self._get_ranked_entries(giocatore)

        for entry in ranked_entries:
            if entry.get("queueType") != queue_type:
                continue

            tier = entry.get("tier", "")
            divisione = entry.get("rank", "")
            tier_numero = RANK_TIERS.get(tier, 0)
            divisione_numero = RANK_DIVISIONI.get(divisione, 0)
            league_points = entry.get("leaguePoints", 0)

            if not divisione_numero and tier in TIER_SENZA_DIVISIONE:
                divisione_numero = 1

            rank_score = rank_score_for_entry(
                tier=tier,
                divisione=divisione,
                league_points=league_points,
            )

            wins = entry.get("wins", 0)
            losses = entry.get("losses", 0)

            return {
                "queue_type": entry.get("queueType", queue_type),
                "tier": tier,
                "tier_numero": tier_numero,
                "divisione": divisione_numero,
                "divisione_nome": divisione,
                "rank_score": rank_score,
                "is_ranked": rank_score is not None,
                "rank_missing": rank_score is None,
                "rank_nome": f"{tier} {divisione}".strip(),
                "league_points": league_points,
                "wins": wins,
                "losses": losses,
                "data": entry,
            }

        return None

    def _get_ranked_entries(self, giocatore: Giocatore) -> list[dict[str, Any]]:
        
        if giocatore.puuid:
            return self.client.league.by_puuid(
                self.config.platform_region,
                giocatore.puuid,
            )

        if giocatore.summoner_id:
            return self.client.league.by_summoner(
                self.config.platform_region,
                giocatore.summoner_id,
            )

        raise ValueError("puuid e summoner_id mancanti: impossibile leggere il rank")
