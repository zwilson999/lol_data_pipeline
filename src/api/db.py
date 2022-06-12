import pymongo
import logging
logger = logging.getLogger(__name__)

from utils.utils import process_json
class Mongo:
    def __init__(self, db: str, collection: str, data: "list[dict]", puuid: str, uri: str="mongodb://localhost:27017/") -> None:
        self.db: str = db
        self.collection: str = collection
        self.data: list[dict] = data # JSON Array
        self.puuid: str = puuid
        self.uri: str = uri
    
    def transform(self) -> dict:

        # Add metadata fields to our JSON array and flatten the json into a list of flat dictionaries for MongoDb consumption
        self.transformed_data: list[dict] = [process_json(d, self.puuid) for d in self.data]
        return self
        
    def load(self) -> None:
        try:
            client = pymongo.MongoClient(self.uri)
            db = client[self.db]
            coll = db[self.collection]
        except:
            logger.info("Could not connect to Mongodb")

        # Clear documents before inserting many
        deleted: pymongo.DeleteResult = coll.delete_many({})
        logger.info(f"Number of Documents deleted {deleted.deleted_count}")

        # Insert all match data
        inserted: pymongo.InsertManyResult = coll.insert_many(self.transformed_data)
        logger.info(f"Number of documents inserted: {len(inserted.inserted_ids)}")
