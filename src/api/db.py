import pymongo
import logging
LOGGER: logging.Logger = logging.getLogger(__name__)
from typing import Optional
from utils.utils import process_json

class Mongo:
    def __init__(self, db: str, collection: str, data: "list[Optional[dict]]", puuid: str, uri: str="mongodb://localhost:27017/") -> None:
        self.db: str = db
        self.collection: str = collection
        self.data: list[Optional[dict]] = data # JSON Array
        self.puuid: str = puuid
        self.uri: str = uri

    def transform(self) -> "Mongo":
        # Add metadata fields to our JSON array and flatten the json into a list of flat dictionaries for MongoDb consumption
        self.transformed_data: list[Optional[dict]] = [
            process_json(d, self.puuid)
            for d in self.data
        ]
        return self

    def load(self) -> None:
        try:
            client = pymongo.MongoClient(self.uri)
            db = client[self.db]
            coll = db[self.collection]
        except:
            LOGGER.info("Could not connect to Mongodb")
            exit()

        # Truncate existing match documents before inserting many
        deleted: pymongo.DeleteResult = coll.delete_many({})
        LOGGER.info(f"Number of Documents deleted {deleted.deleted_count}")

        # Insert all match data
        inserted: pymongo.InsertManyResult = coll.insert_many(self.transformed_data)
        LOGGER.info(f"Number of documents inserted: {len(inserted.inserted_ids)}")
