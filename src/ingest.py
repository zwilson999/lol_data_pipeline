import requests
import argparse
import utils.util as utils
import pymongo
from datetime import datetime
from time import sleep

class LeagueApi:
    """
    Class to ingest data from Riot API for League of Legends
    """
    def __init__(self, api_key: str, summoner: str, queue_types: "list[str]", db: str, collection: str):
        self.api_key: str = api_key
        self.summoner: str = summoner
        self.queue_types: list[str] = queue_types
        self.bad_status_codes: list[int] = [400, 401, 403, 404, 405, 415, 429, 500, 502, 503, 504]
        self.headers: dict = self.get_headers()
        self.get_summoners_url: str = "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/"
        self.get_match_data_url: str = "https://americas.api.riotgames.com/lol/match/v5/matches/"
        self.db: str = db
        self.collection: str = collection
    
    def get_headers(self) -> dict:
        headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)     Chrome/86.0.4240.183 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://developer.riotgames.com",
            "X-Riot-Token": self.api_key # API key
        }
        return headers

    def get_puuid(self) -> "LeagueApi":
        try:
            resp: dict = requests.get(self.get_summoners_url + self.summoner, headers=self.headers)
            if resp.status_code == 200:
                data: dict = resp.json()
                self.encrypted_account_id: str = data['accountId']
                self.puuid: str = data['puuid']
                print("Successfully authenticated.")
        except:
            print("Make sure your API Key is refreshed. You can request a permanent API Key at: https://developer.riotgames.com/app-type")
            print(f"Response code: {resp.status_code}")
        return self

    def get_matches(self) -> "LeagueApi":

        matches: list = []
        query: dict = None 
        for q in self.queue_types:
            print(f"Getting all {q} Matches...")
            for i in range(0, 2000, 100):
                query: dict = {
                    'queue': utils.get_queue_id(q), # Queue type
                    'start': i, # Index start
                    'count': 100 # How many matches to pull in a single query (max=100)
                }
                resp: list = requests.get(f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puuid}/ids", headers=self.headers, params=query).json()
                matches.extend(resp)

        # Remove duplicate matches
        if len(matches) != len(set(matches)):
            self.matches: list[str] = list(set(matches))
            print("Duplicate Matches Removed")
        else:
            self.matches: list[str] = list(matches)

        print(f"There are {len(self.matches)} total matches...")
        return self
    
    def get_match_data(self) -> "LeagueApi":

        def find_participant_idx(body: dict, value: str) -> int:
            """
            args:
                body = list of dicts which we want to traverse to find the index of the matching dictionary that contains the desired puuid
                value = the puuid we want to search to find the proper dictionary
            """
            idx: int = None
            if len(body['metadata']['participants']) == 0:
                print("Body has no elements to search")
                return
            
            for i in range(len(body['metadata']['participants'])):
                if body['metadata']['participants'][i]==value:
                    idx: int = i
            return idx  

        self.match_data: list[dict] = [] # capture all match dictionaries in a list
        participant_idx: int = None
        starttime: datetime.datetime = datetime.now()
        for i, match in enumerate(self.matches):

            resp = requests.get(self.get_match_data_url + match, headers=self.headers)
            while resp.status_code in self.bad_status_codes:
                sleep(60)
                resp = requests.get(self.get_match_data_url + match, headers=self.headers)
                if resp.status_code not in self.bad_status_codes:
                    break
            
            data: dict = resp.json()
            participant_idx: int = find_participant_idx(data, self.puuid) # Find index of desired summoner so we know which summoner info to pull
            
            # According to Match API Docs, if gameEndTimestamp is NOT in the response, treat game_duration as milliseconds, else treat it as seconds.
            # NOTE: gameEndTimestamp was added on October 5th, 2021
            try:
                d: dict = {
                    'matchId': match,
                    'gameCreation': data['info']['gameCreation'], # When the game was created in unix timestamp milliseconds
                    'gameCreationDate': utils.unix_timestamp_to_date(data['info']['gameCreation']),
                    'gameDuration': data['info']['gameDuration'],
                    'gameDurationUnits': 's',
                    'gameStartTimestamp': data['info']['gameStartTimestamp'],
                    'gameStartTimestampDate': utils.unix_timestamp_to_date(data['info']['gameStartTimestamp']),
                    'gameEndTimestamp': data['info']['gameEndTimestamp'],
                    'gameEndTimestampDate': utils.unix_timestamp_to_date(data['info']['gameEndTimestamp']),
                    'gameId': data['info']['gameId'],
                    'gameMode': data['info']['gameMode'],
                    'gameName': data['info']['gameName'],
                    'gameType': data['info']['gameType'],
                    'gameVersion': data['info']['gameVersion'],
                    'mapId': data['info']['mapId'],
                }
            # Handle no gameEndTimestamp field
            except KeyError:
                d: dict = {
                    'matchId': match,
                    'gameCreation': data['info']['gameCreation'], # When the game was created in unix timestamp milliseconds
                    'gameCreationDate': utils.unix_timestamp_to_date(data['info']['gameCreation']),
                    'gameDuration': data['info']['gameDuration'],
                    'gameDurationUnits': 'ms',
                    'gameStartTimestamp': data['info']['gameStartTimestamp'],
                    'gameStartTimestampDate': utils.unix_timestamp_to_date(data['info']['gameStartTimestamp']),
                    'gameEndTimestamp': None,
                    'gameEndTimestampDate': None,
                    'gameId': data['info']['gameId'],
                    'gameMode': data['info']['gameMode'],
                    'gameName': data['info']['gameName'],
                    'gameType': data['info']['gameType'],
                    'gameVersion': data['info']['gameVersion'],
                    'mapId': data['info']['mapId'],
                }
            d.update(utils.flatten_nested_json(data['info']['participants'][participant_idx]))
            self.match_data.append(d)
            print(f"{i}: Match Id: {match} appended.")

        print(datetime.now() - starttime)
        return self

    def write_to_mongo(self) -> None:
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client[self.db]
            coll = db[self.collection]
        except:
            print("Could not connect to Mongodb")

        # Clear documents before inserting many
        deleted = coll.delete_many({})
        print(f"Number of Documents deleted {deleted.deleted_count}")

        # Insert all match data
        inserted = coll.insert_many(self.match_data)
        print(f"Number of documents inserted: {len(inserted.inserted_ids)}")

def get_api_key(key_path: str) -> str:
    try:
        with open(key_path, 'r') as f:
            api_key: str = f.read()
            f.close()
        return api_key
    except FileNotFoundError:
        exit("Text file with API key not provided correctly... Check your file path.")

def main(args: argparse.Namespace) -> None:
    
    api_key: str = get_api_key(args.api_key_path)
    api: LeagueApi = LeagueApi(api_key, args.summoner, queue_types=args.queue_type, db=args.db, collection=args.collection)
    (api.get_puuid()
        .get_matches()
        .get_match_data()
        .write_to_mongo())

if __name__ == "__main__":
    parser: argparse.ArgumentParser() = argparse.ArgumentParser()
    parser.add_argument("--api_key_path", type=str, required=False, default="../creds/api_key.txt", help="API Key path stored in a .txt file for authentication.")
    parser.add_argument("--summoner", type=str, required=True, help="The name of the League Summoner you want to pull data for.")
    parser.add_argument("--queue_type", required=True, choices=["draft", "blind", "aram"], nargs='+', help="Choice of queue type to pull data for.")
    parser.add_argument("--db", required=True, help="Name of Local MongoDb database to insert data into.")
    parser.add_argument("--collection", required=True, help="Name of local collection stored in the --db argument.")
    args: argparse.Namespace = parser.parse_args()
    main(args)