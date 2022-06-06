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

def unix_timestamp_to_date(timestamp: int) -> str:
    from datetime import datetime
    """
        args:
            timestamp: integer timestamp in milliseconds
        returns:
            converted timestamp in MS to YYY-MM-DD string date format
    """
    converted_date: str = datetime.fromtimestamp(timestamp / 1000.0).strftime("%Y-%m-%d")
    return converted_date
