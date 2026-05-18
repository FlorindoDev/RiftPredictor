from riotwatcher import LolWatcher

from .config import RiotConfig


def create_client(config: RiotConfig) -> LolWatcher:
    return LolWatcher(config.api_key)
