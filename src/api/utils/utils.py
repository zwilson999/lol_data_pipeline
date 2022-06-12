import logging
logger = logging.getLogger(__name__)

def flatten_nested_json(d: dict) -> dict:
    """
    Accepts Dictionary argument which can have nested dictionaries/lists within.
    Output will be a flat dictionary that can be converted to a pandas dataframe
    """
    out: dict = {}
    def flatten(x, name: str=''):
        # Handles dictionaries with elements
        if type(x) is dict:
            for k in x:
                flatten(x[k], name + k + "_")
        # Handles lists with elements
        elif type(x) is list:
            for j in x: # for item in list
                flatten(j)
        else:
            out[name[:-1]] = x
    flatten(d)
    return out

# def flatten_data(d: dict):
#     out = {}

#     def flatten(x, name=''):
#         if type(x) is dict:
#             for a in x:
#                 flatten(x[a], name + a + '_')
#         elif type(x) is list:
#             i = 0
#             for a in x:
#                 flatten(a, name + str(i) + '_')
#                 i += 1
#         else:
#             out[name[:-1]] = x

#     flatten(d)
#     return out

def get_queue_id(queue_type: str) -> int:
    """
    Get all match IDs by queue type code.
    Queue Type Code Lookup:
        400: Draft 5v5
        430: Blind Pick 5v5
        450: ARAM 
    """
    match_type_map: dict = {
        "draft": 400,
        "blind": 430,
        "aram": 450
    }
    return match_type_map[queue_type]

def process_json(data: dict, participant: str) -> dict:
    """
    This function will take the base match data JSON response and add metadata fields such as date fields in proper formats.
    It will also flatten necessary nested components of our resulting json from API
    """
    
    def unix_timestamp_to_date(timestamp: float) -> str:
        from datetime import datetime
        """
            args:
                timestamp: integer timestamp in milliseconds
            returns:
                converted timestamp in MS to YYY-MM-DD string date format
        """
        converted_date: str = datetime.fromtimestamp(timestamp / 1000.0).strftime("%Y-%m-%d")
        return converted_date

    def find_participant_idx(body: dict, value: str) -> int:
        """
        args:
            body = list of dicts which we want to traverse to find the index of the matching dictionary that contains the desired puuid
            value = the puuid we want to search to find the proper dictionary
        """
        idx: int = None
        if len(body['metadata']['participants']) == 0:
            logger.info("Body has no elements to search")
            return
        # Search through participans to find the index of our summoner.
        for i in range(len(body['metadata']['participants'])):
            if body['metadata']['participants'][i] == value:
                idx: int = i
        return idx

    # According to Match API Docs, if gameEndTimestamp is NOT in the response, treat game_duration as milliseconds, else treat it as seconds.
    # NOTE: gameEndTimestamp was added on October 5th, 2021
    try:
        d: dict = {
            'matchId': data['metadata']['matchId'],
            'gameCreation': data['info']['gameCreation'], # When the game was created in unix timestamp milliseconds
            'gameCreationDate': unix_timestamp_to_date(data['info']['gameCreation']),
            'gameDuration': data['info']['gameDuration'],
            'gameDurationUnits': 's',
            'gameStartTimestamp': data['info']['gameStartTimestamp'],
            'gameStartTimestampDate': unix_timestamp_to_date(data['info']['gameStartTimestamp']),
            'gameEndTimestamp': data['info']['gameEndTimestamp'],
            'gameEndTimestampDate': unix_timestamp_to_date(data['info']['gameEndTimestamp']),
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
            'matchId': data['metadata']['matchId'],
            'gameCreation': data['info']['gameCreation'], # When the game was created in unix timestamp milliseconds
            'gameCreationDate': unix_timestamp_to_date(data['info']['gameCreation']),
            'gameDuration': data['info']['gameDuration'],
            'gameDurationUnits': 'ms',
            'gameStartTimestamp': data['info']['gameStartTimestamp'],
            'gameStartTimestampDate': unix_timestamp_to_date(data['info']['gameStartTimestamp']),
            'gameEndTimestamp': None,
            'gameEndTimestampDate': None,
            'gameId': data['info']['gameId'],
            'gameMode': data['info']['gameMode'],
            'gameName': data['info']['gameName'],
            'gameType': data['info']['gameType'],
            'gameVersion': data['info']['gameVersion'],
            'mapId': data['info']['mapId'],
        }

    # Update the final JSON output with participant data.
    participant_idx: int = find_participant_idx(data, participant)
    d.update(flatten_nested_json(data['info']['participants'][participant_idx]))
    logger.info(f"Match Id: {d['matchId']} processed.")

    return d