from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class RiotConfig:
    api_key: str
    platform_region: str


def load_config(env_path: str | Path | None = None) -> RiotConfig:

    dotenv_path = Path(env_path) if env_path else Path(__file__).resolve().parents[2] / ".env"

    load_dotenv(dotenv_path=dotenv_path)

    api_key = os.getenv("RIOT_API_KEY")
    platform_region = os.getenv("RIOT_PLATFORM_REGION")

    if not api_key:
        raise ValueError("Missing RIOT_API_KEY in environment")
    if not platform_region:
        raise ValueError("Missing RIOT_PLATFORM_REGION in environment")

    return RiotConfig(
        api_key=api_key,
        platform_region=platform_region.upper(),
    )
