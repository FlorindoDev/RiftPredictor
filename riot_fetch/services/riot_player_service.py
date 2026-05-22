from __future__ import annotations

from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config
from ..models.giocatore import Giocatore


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

    def get_info_player(
        self,
        giocatore: Giocatore,
        queue_type: str = "RANKED_SOLO_5x5",
    ) -> dict[str, Any] | None:
        if not giocatore.summoner_id:
            raise ValueError("summoner_id mancante: impossibile leggere il rank")

        ranked_entries = self.client.league.by_summoner(
            self.config.platform_region,
            giocatore.summoner_id,
        )

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

            return {
                "queue_type": entry.get("queueType", queue_type),
                "tier": tier,
                "tier_numero": tier_numero,
                "divisione": divisione_numero,
                "divisione_nome": divisione,
                "rank": rank,
                "rank_nome": f"{tier} {divisione}".strip(),
                "league_points": entry.get("leaguePoints", 0),
                "wins": entry.get("wins", 0),
                "losses": entry.get("losses", 0),
                "data": entry,
            }

        return None
