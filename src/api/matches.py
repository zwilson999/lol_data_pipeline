import requests
import time
import logging
logger = logging.getLogger(__name__)
from utils.utils import get_queue_id


"""
Alter this later if you have more matches than this in your game history.
Thats a lot of matches!!!
"""
NUM_MATCHES_TO_SEARCH = 1000

class SummonerMatches:

    def __init__(self, api_key: str, puuid: str, queue_types: "list[str]") -> None:
        self.api_key: str = api_key
        self.puuid: str = puuid
        self.url: str = "https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/SUMMONER_PUUID/ids"
        self.queue_types: list[str] = queue_types

    def get_matches(self) -> "list[str]":
        headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)     Chrome/86.0.4240.183 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com",
            "X-Riot-Token": self.api_key # API key
        }
        matches: list = []
        query: dict = None 
        for q in self.queue_types:
            logger.info(f"Getting all {q} Matches...")
            for i in range(0, NUM_MATCHES_TO_SEARCH, 100):
                query: dict = {
                    'queue': get_queue_id(q), # Queue type
                    'start': i, # Index start
                    'count': 100 # How many matches to pull in a single query (max=100)
                }
                url: str = self.url.replace("SUMMONER_PUUID", self.puuid)
                resp: list = requests.get(url=url, headers=headers, params=query)
                while resp.status_code == 429:
                    time.sleep(120)
                    url: str = self.url.replace("SUMMONER_PUUID", self.puuid)
                    resp: list = requests.get(url=url, headers=headers, params=query).json()
                else:
                    if resp.status_code == 200:
                        matches.extend(resp.json())

        # Remove duplicate matches
        if len(matches) != len(set(matches)):
            self.matches: list[str] = list(set(matches))
            logger.info("Duplicate Matches Removed")
        else:
            self.matches: list[str] = list(matches)

        logger.info(f"There are {len(self.matches)} total matches...")
        return matches