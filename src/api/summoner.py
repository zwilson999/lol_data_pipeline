import requests
import logging
LOGGER: logging.Logger = logging.getLogger(__name__)
class Summoner:
    def __init__(self, api_key: str, summoner_name: str) -> None:
        self.api_key: str = api_key
        self.summoner_name: str = summoner_name
        self.url: str = "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/"

    def get_puuid(self) -> str:
        headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)     Chrome/86.0.4240.183 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com",
            "X-Riot-Token": self.api_key # API key
        }
        try:
            resp: dict = requests.get(self.url + self.summoner_name, headers=headers)
            if resp.status_code == 200:
                data: dict = resp.json()
                puuid: str = data['puuid']
                LOGGER.info("Successfully authenticated.")
            else:
                LOGGER.info(f"Could not authenticate. Response status: {resp.status_code}")
        except:
            LOGGER.error("Make sure your API Key is refreshed. You can request a permanent API Key at: https://developer.riotgames.com/app-type")
            LOGGER.error(f"Response code: {resp.status_code}")
        return puuid     