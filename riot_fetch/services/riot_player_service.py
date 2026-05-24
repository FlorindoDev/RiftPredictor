from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..models.giocatore import Giocatore
from ..models.squadra import Squadra


RANK_TIERS = {
    "IRON": 1,
    "BRONZE": 2,
    "SILVER": 3,
    "GOLD": 4,
    "PLATINUM": 5,
    "EMERALD": 6,
    "DIAMOND": 7,
    "MASTER": 8,
    "GRANDMASTER": 9,
    "CHALLENGER": 10,
}

RANK_DIVISIONI = {
    "IV": 4,
    "III": 3,
    "II": 2,
    "I": 1,
}

_TIER_SENZA_DIVISIONE = {"MASTER", "GRANDMASTER", "CHALLENGER"}


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
            champion_mastery = self.get_champion(giocatore)["mastery"]
            composition.append(
                {
                    "team_position": giocatore.team_position,
                    "champion_name": giocatore.champion_name,
                    "role": giocatore.role,
                    "champion_mastery": champion_mastery.get("championLevel", 0),
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

            if not divisione_numero and tier in _TIER_SENZA_DIVISIONE:
                divisione_numero = 1

            rank = 0
            if tier_numero and divisione_numero:
                rank = ((tier_numero - 1) * 4) + (5 - divisione_numero)

            wins = entry.get("wins", 0)
            losses = entry.get("losses", 0)
            games_count = wins + losses

            return {
                "queue_type": entry.get("queueType", queue_type),
                "tier": tier,
                "tier_numero": tier_numero,
                "divisione": divisione_numero,
                "divisione_nome": divisione,
                "rank": rank,
                "rank_nome": f"{tier} {divisione}".strip(),
                "league_points": entry.get("leaguePoints", 0),
                "wins": wins,
                "losses": losses,
                "winrate": round((wins / games_count) * 100, 2) if games_count else 0,
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
