import asyncio
import aiohttp
import argparse
import time
import logging
from typing import Optional
from datetime import datetime
from matches import SummonerMatches
from summoner import Summoner
from db import Mongo
from utils.utils import Request, Response

LOGGER: logging.Logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("../../logs/logs.log"),
        logging.StreamHandler()
    ]
)
class SummonerMatchData:

    def __init__(self, api_key: str, matches: "list[str]", rate_limit: int) -> None:
        self.event_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.rate_limit: int = rate_limit
        self.matches: list[str] = matches
        self.api_key: str = api_key

    def prepare(self) -> "SummonerMatchData":
        self.requests: list[Request] = [
            Request(method='get', url=f"https://americas.api.riotgames.com/lol/match/v5/matches/{m}")
            for m in self.matches
        ]
        return self

    def run(self) -> "list[Response]":
        LOGGER.info(f"Starting async requests with rate limit {self.rate_limit}/s Total Requests to make: {len(self.matches)}")

        # Return all responses after making Async requests
        responses: list[Response] = self.event_loop.run_until_complete(_make_requests(self.api_key, *self.requests, rate_limit=self.rate_limit))
        LOGGER.info(f"There are {len(responses)} responses received")

        # Filter out non-200 responses
        final_responses = [r for r in responses if r.status == 200]
        LOGGER.info(f"There are {len(responses) - len(final_responses)} non-OK responses")
        return final_responses

async def _make_requests(api_key: str, *requests, rate_limit: int) -> "list[Response]":
    semaphore: asyncio.Semaphore = asyncio.Semaphore(rate_limit)
    headers: dict = {
        "Accept": "application/json",
        "X-Riot-Token": api_key # API key
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks: list[asyncio.Task] = [asyncio.create_task(_iterate(semaphore, session, request)) for request in requests]
        responses = await asyncio.gather(*tasks)
    return responses

async def _iterate(semaphore: asyncio.Semaphore, session: aiohttp.ClientSession, request: Request) -> Response:
    async with semaphore:
        return await _fetch(session, request)

async def _fetch(session: aiohttp.ClientSession, request: Request) -> Response:
    async with session.request(request.method, request.url) as response:
        try:
            content: dict = await response.json()
            response.raise_for_status()
            await asyncio.sleep(1.0)
            return Response(request.url, response.status, payload=content, error=False)
        except aiohttp.ContentTypeError:
            LOGGER.info(f"Response Status: {response.status}.")
            await asyncio.sleep(1.0)
            return Response(request.url, response.status, error=True)
        except aiohttp.ClientResponseError:
            if response.status == 429:
                wait: int = int(response.headers['Retry-After']) # Wait for as many seconds as the API response headers say.
                LOGGER.info(f"Waiting {wait}")
                await asyncio.sleep(wait)
                return await _fetch(session, request)

def get_api_key(api_key_path: str) -> str:
    """
    Load Riot Games API Key from text file path.
    """
    try:
        with open(api_key_path, 'r') as f:
            api_key: str = f.read()
        return api_key
    except FileNotFoundError:
        raise FileNotFoundError("Text file with API key not provided correctly... Check your file path.")

def main(args: argparse.Namespace) -> None:

    # Retrieve non-expiring API Key from TXT file.
    api_key: str = get_api_key(args.api_key_path)

    # Retrieve unique summoner PUUID which we will use to access other endpoints.
    puuid: str = Summoner(api_key=api_key, summoner_name=args.summoner).get_puuid()

    # Retrieve an iterable of all matchIds we will use as input to retrieve match data in match data endpoint
    matches: list[str] = SummonerMatches(api_key=api_key, puuid=puuid, queue_types=args.queue_type).get_matches()

    # Query Match Data Endpoint and return JSON of all desired match data
    # Rate limit is n requests /s
    time.sleep(125) # Back off 2 minutes before sending async requests to match data (since we already sent some requests as prerequisites)
    start_time: datetime = datetime.now()
    responses: list[Response] = (SummonerMatchData(api_key=api_key, matches=matches, rate_limit=args.rate_limit)
                                    .prepare()
                                    .run())
    LOGGER.info(f"Requests took {datetime.now() - start_time}")

    # Extract json payloads into list
    payloads: list[Optional[dict]] = [resp.payload for resp in responses]

    # Process selected summoner data to MongoDb
    Mongo(args.db, args.collection, data=payloads, puuid=puuid).transform().load()

if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--api_key_path", type=str, required=False, default="../../creds/api_key.txt", help="API Key path stored in a .txt file for authentication.")
    parser.add_argument("--summoner", type=str, required=True, help="The name of the League Summoner you want to pull data for.")
    parser.add_argument("--queue_type", required=True, default='draft', choices=["draft", "blind", "aram"], nargs='+', help="Choice of queue type to pull data for.")
    parser.add_argument("--db", type=str, required=False, default='league_of_legends', help="Name of Local MongoDb database to insert data into.")
    parser.add_argument("--collection", required=False, default='match_data', help="Name of local collection stored in the --db argument.")
    parser.add_argument("--rate_limit", required=False, default=20, help="The required rate limit per second by the API (Currently is 20/s)")
    args: argparse.Namespace = parser.parse_args()
    main(args)
