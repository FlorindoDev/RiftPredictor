from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from riotwatcher import LolWatcher

from ..client_riot import RiotConfig, create_client, load_config


_PING_FIELDS = (
    "allInPings",
    "assistMePings",
    "basicPings",
    "commandPings",
    "dangerPings",
    "enemyMissingPings",
    "enemyVisionPings",
    "getBackPings",
    "holdPings",
    "needVisionPings",
    "onMyWayPings",
    "pushPings",
    "retreatPings",
    "visionClearedPings",
)

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


@dataclass
class Giocatore:
    participant_id: int
    puuid: str
    summoner_id: str
    summoner_name: str
    summoner_level: int
    riot_id_game_name: str
    riot_id_tagline: str
    profile_icon: int

    team_id: int
    team_position: str
    individual_position: str
    lane: str
    role: str
    win: bool

    champion_id: int
    champion_name: str
    champion_level: int
    champion_experience: int
    champion_transform: int

    kills: int
    deaths: int
    assists: int
    double_kills: int
    triple_kills: int
    quadra_kills: int
    penta_kills: int
    unreal_kills: int
    largest_multi_kill: int
    killing_sprees: int
    largest_killing_spree: int
    first_blood_kill: bool
    first_blood_assist: bool
    first_tower_kill: bool
    first_tower_assist: bool

    gold_earned: int
    gold_spent: int
    total_minions_killed: int
    neutral_minions_killed: int
    total_ally_jungle_minions_killed: int
    total_enemy_jungle_minions_killed: int

    total_damage_dealt: int
    total_damage_dealt_to_champions: int
    total_damage_taken: int
    total_damage_shielded_on_teammates: int
    total_heal: int
    total_heals_on_teammates: int
    damage_self_mitigated: int
    magic_damage_dealt: int
    magic_damage_dealt_to_champions: int
    magic_damage_taken: int
    physical_damage_dealt: int
    physical_damage_dealt_to_champions: int
    physical_damage_taken: int
    true_damage_dealt: int
    true_damage_dealt_to_champions: int
    true_damage_taken: int

    damage_dealt_to_buildings: int
    damage_dealt_to_objectives: int
    damage_dealt_to_turrets: int
    damage_dealt_to_epic_monsters: int
    baron_kills: int
    dragon_kills: int
    inhibitor_kills: int
    inhibitor_takedowns: int
    inhibitors_lost: int
    nexus_kills: int
    nexus_takedowns: int
    nexus_lost: int
    objectives_stolen: int
    objectives_stolen_assists: int
    turret_kills: int
    turret_takedowns: int
    turrets_lost: int

    vision_score: int
    vision_wards_bought_in_game: int
    detector_wards_placed: int
    sight_wards_bought_in_game: int
    wards_killed: int
    wards_placed: int

    items: list[int]
    items_purchased: int
    summoner1_id: int
    summoner1_casts: int
    summoner2_id: int
    summoner2_casts: int
    spell1_casts: int
    spell2_casts: int
    spell3_casts: int
    spell4_casts: int

    time_played: int
    time_ccing_others: int
    total_time_cc_dealt: int
    total_time_spent_dead: int
    longest_time_spent_living: int
    consumables_purchased: int

    perks: dict[str, Any]
    challenges: dict[str, Any]
    missions: dict[str, Any]
    pings: dict[str, int]
    data: dict[str, Any] = field(repr=False)

    @classmethod
    def from_match_data(cls, player_data: dict[str, Any]) -> Giocatore:
        return cls(
            participant_id=player_data.get("participantId", 0),
            puuid=player_data.get("puuid", ""),
            summoner_id=player_data.get("summonerId", ""),
            summoner_name=player_data.get("summonerName", ""),
            summoner_level=player_data.get("summonerLevel", 0),
            riot_id_game_name=player_data.get("riotIdGameName", ""),
            riot_id_tagline=player_data.get("riotIdTagline", ""),
            profile_icon=player_data.get("profileIcon", 0),
            team_id=player_data.get("teamId", 0),
            team_position=player_data.get("teamPosition", ""),
            individual_position=player_data.get("individualPosition", ""),
            lane=player_data.get("lane", ""),
            role=player_data.get("role", ""),
            win=player_data.get("win", False),
            champion_id=player_data.get("championId", 0),
            champion_name=player_data.get("championName", ""),
            champion_level=player_data.get("champLevel", 0),
            champion_experience=player_data.get("champExperience", 0),
            champion_transform=player_data.get("championTransform", 0),
            kills=player_data.get("kills", 0),
            deaths=player_data.get("deaths", 0),
            assists=player_data.get("assists", 0),
            double_kills=player_data.get("doubleKills", 0),
            triple_kills=player_data.get("tripleKills", 0),
            quadra_kills=player_data.get("quadraKills", 0),
            penta_kills=player_data.get("pentaKills", 0),
            unreal_kills=player_data.get("unrealKills", 0),
            largest_multi_kill=player_data.get("largestMultiKill", 0),
            killing_sprees=player_data.get("killingSprees", 0),
            largest_killing_spree=player_data.get("largestKillingSpree", 0),
            first_blood_kill=player_data.get("firstBloodKill", False),
            first_blood_assist=player_data.get("firstBloodAssist", False),
            first_tower_kill=player_data.get("firstTowerKill", False),
            first_tower_assist=player_data.get("firstTowerAssist", False),
            gold_earned=player_data.get("goldEarned", 0),
            gold_spent=player_data.get("goldSpent", 0),
            total_minions_killed=player_data.get("totalMinionsKilled", 0),
            neutral_minions_killed=player_data.get("neutralMinionsKilled", 0),
            total_ally_jungle_minions_killed=player_data.get(
                "totalAllyJungleMinionsKilled",
                0,
            ),
            total_enemy_jungle_minions_killed=player_data.get(
                "totalEnemyJungleMinionsKilled",
                0,
            ),
            total_damage_dealt=player_data.get("totalDamageDealt", 0),
            total_damage_dealt_to_champions=player_data.get(
                "totalDamageDealtToChampions",
                0,
            ),
            total_damage_taken=player_data.get("totalDamageTaken", 0),
            total_damage_shielded_on_teammates=player_data.get(
                "totalDamageShieldedOnTeammates",
                0,
            ),
            total_heal=player_data.get("totalHeal", 0),
            total_heals_on_teammates=player_data.get("totalHealsOnTeammates", 0),
            damage_self_mitigated=player_data.get("damageSelfMitigated", 0),
            magic_damage_dealt=player_data.get("magicDamageDealt", 0),
            magic_damage_dealt_to_champions=player_data.get(
                "magicDamageDealtToChampions",
                0,
            ),
            magic_damage_taken=player_data.get("magicDamageTaken", 0),
            physical_damage_dealt=player_data.get("physicalDamageDealt", 0),
            physical_damage_dealt_to_champions=player_data.get(
                "physicalDamageDealtToChampions",
                0,
            ),
            physical_damage_taken=player_data.get("physicalDamageTaken", 0),
            true_damage_dealt=player_data.get("trueDamageDealt", 0),
            true_damage_dealt_to_champions=player_data.get(
                "trueDamageDealtToChampions",
                0,
            ),
            true_damage_taken=player_data.get("trueDamageTaken", 0),
            damage_dealt_to_buildings=player_data.get("damageDealtToBuildings", 0),
            damage_dealt_to_objectives=player_data.get("damageDealtToObjectives", 0),
            damage_dealt_to_turrets=player_data.get("damageDealtToTurrets", 0),
            damage_dealt_to_epic_monsters=player_data.get(
                "damageDealtToEpicMonsters",
                0,
            ),
            baron_kills=player_data.get("baronKills", 0),
            dragon_kills=player_data.get("dragonKills", 0),
            inhibitor_kills=player_data.get("inhibitorKills", 0),
            inhibitor_takedowns=player_data.get("inhibitorTakedowns", 0),
            inhibitors_lost=player_data.get("inhibitorsLost", 0),
            nexus_kills=player_data.get("nexusKills", 0),
            nexus_takedowns=player_data.get("nexusTakedowns", 0),
            nexus_lost=player_data.get("nexusLost", 0),
            objectives_stolen=player_data.get("objectivesStolen", 0),
            objectives_stolen_assists=player_data.get("objectivesStolenAssists", 0),
            turret_kills=player_data.get("turretKills", 0),
            turret_takedowns=player_data.get("turretTakedowns", 0),
            turrets_lost=player_data.get("turretsLost", 0),
            vision_score=player_data.get("visionScore", 0),
            vision_wards_bought_in_game=player_data.get(
                "visionWardsBoughtInGame",
                0,
            ),
            detector_wards_placed=player_data.get("detectorWardsPlaced", 0),
            sight_wards_bought_in_game=player_data.get("sightWardsBoughtInGame", 0),
            wards_killed=player_data.get("wardsKilled", 0),
            wards_placed=player_data.get("wardsPlaced", 0),
            items=[player_data.get(f"item{index}", 0) for index in range(7)],
            items_purchased=player_data.get("itemsPurchased", 0),
            summoner1_id=player_data.get("summoner1Id", 0),
            summoner1_casts=player_data.get("summoner1Casts", 0),
            summoner2_id=player_data.get("summoner2Id", 0),
            summoner2_casts=player_data.get("summoner2Casts", 0),
            spell1_casts=player_data.get("spell1Casts", 0),
            spell2_casts=player_data.get("spell2Casts", 0),
            spell3_casts=player_data.get("spell3Casts", 0),
            spell4_casts=player_data.get("spell4Casts", 0),
            time_played=player_data.get("timePlayed", 0),
            time_ccing_others=player_data.get("timeCCingOthers", 0),
            total_time_cc_dealt=player_data.get("totalTimeCCDealt", 0),
            total_time_spent_dead=player_data.get("totalTimeSpentDead", 0),
            longest_time_spent_living=player_data.get("longestTimeSpentLiving", 0),
            consumables_purchased=player_data.get("consumablesPurchased", 0),
            perks=player_data.get("perks", {}),
            challenges=player_data.get("challenges", {}),
            missions=player_data.get("missions", {}),
            pings={name: player_data.get(name, 0) for name in _PING_FIELDS},
            data=player_data,
        )

    @property
    def kda(self) -> float:
        return round((self.kills + self.assists) / max(1, self.deaths), 2)

    def get_champion(
        self,
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
    ) -> dict[str, Any]:
        if not self.puuid:
            raise ValueError("puuid mancante: impossibile leggere la champion mastery")
        if not self.champion_id:
            raise ValueError("champion_id mancante: impossibile leggere la champion mastery")

        riot_config = config or load_config()
        riot_client = client or create_client(riot_config)
        mastery = riot_client.champion_mastery.by_puuid_by_champion(
            riot_config.platform_region,
            self.puuid,
            self.champion_id,
        )

        return {
            "champion_id": self.champion_id,
            "champion_name": self.champion_name,
            "mastery": mastery,
        }

    def get_info_player(
        self,
        queue_type: str = "RANKED_SOLO_5x5",
        config: RiotConfig | None = None,
        client: LolWatcher | None = None,
    ) -> dict[str, Any] | None:
        if not self.summoner_id:
            raise ValueError("summoner_id mancante: impossibile leggere il rank")

        riot_config = config or load_config()
        riot_client = client or create_client(riot_config)
        ranked_entries = riot_client.league.by_summoner(
            riot_config.platform_region,
            self.summoner_id,
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
