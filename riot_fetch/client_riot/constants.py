PLATFORM_TO_ROUTING_REGION = {
    "BR1": "AMERICAS",
    "LA1": "AMERICAS",
    "LA2": "AMERICAS",
    "NA1": "AMERICAS",
    "EUN1": "EUROPE",
    "EUW1": "EUROPE",
    "RU": "EUROPE",
    "TR1": "EUROPE",
    "JP1": "ASIA",
    "KR": "ASIA",
    "OC1": "SEA",
    "PH2": "SEA",
    "SG2": "SEA",
    "TH2": "SEA",
    "TW2": "SEA",
    "VN2": "SEA",
}

ROUTING_REGIONS = {"AMERICAS", "ASIA", "EUROPE", "SEA"}

METAL_TIERS = (
    "IRON",
    "BRONZE",
    "SILVER",
    "GOLD",
    "PLATINUM",
    "EMERALD",
    "DIAMOND",
)
APEX_TIERS = ("MASTER", "GRANDMASTER", "CHALLENGER")
DIVISIONS = ("I", "II", "III", "IV")
APEX_ENDPOINTS = {
    "MASTER": "masterleagues",
    "GRANDMASTER": "grandmasterleagues",
    "CHALLENGER": "challengerleagues",
}
QUEUE_ALIASES = {
    "RANKED_SOLO_5X5": "RANKED_SOLO_5x5",
    "RANKED_SOLO_5x5": "RANKED_SOLO_5x5",
    "SOLO": "RANKED_SOLO_5x5",
    "RANKED_FLEX_SR": "RANKED_FLEX_SR",
    "FLEX": "RANKED_FLEX_SR",
}
QUEUE_TO_MATCH_QUEUE = {
    "RANKED_SOLO_5x5": 420,
    "RANKED_FLEX_SR": 440,
}

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
TIER_SENZA_DIVISIONE = {"MASTER", "GRANDMASTER", "CHALLENGER"}
APEX_TIER_BASE_SCORE = {
    "MASTER": 29,
    "GRANDMASTER": 30,
    "CHALLENGER": 31,
}


def routing_region_for_platform(platform_region: str) -> str:
    region = platform_region.upper()
    if region in ROUTING_REGIONS:
        return region

    try:
        return PLATFORM_TO_ROUTING_REGION[region]
    except KeyError as exc:
        raise ValueError(f"Unsupported Riot platform region: {platform_region}") from exc
