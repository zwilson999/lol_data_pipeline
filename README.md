# League of Legends Summoner Data Pipeline

This is a simple data pipeline to pull League of Legends Match Data for a given summoner and ingest it into a local MongoDB collection.

Code is setup to pull data into a MongoDb collection I set up locally called ```league_of_legends.match_data```. You can change this to fit your needs.


### Setup

1). Request a personal API Key (that doesn't expire) from the Riot Games team [here.](https://developer.riotgames.com/)

2). Create a .txt file with your API Key and store it in a directory next to ```src``` called ```creds/api_key.txt``` 

NOTE: You can also use an optional argument when calling the main ```pipeline.py``` script with flag --api_key_path to point to the file on your local machine.

3). Prerequisites: Set up MongoDb on your local machine and provide the --db and --collection flag when calling the above script. By default the code is set up to run on your ```localhost:27017```. You can edit the ```write_to_mongo()``` class method in ```pipeline.py```. For example I created a database called ```league_of_legends``` with a collection called ```match_data``` to store my data.

4). Main functionality is ```pipeline.py```. An example call to run the ingestion is below:

```
cd lol_data_pipeline/src/api

# if you have a space in your_league_summoner_name_, be sure to send the argument enclosed in double quotes.
python pipeline.py --summoner <your_league_summoner_name> --queue_type draft blind aram --db league_of_legends --collection match_data
```
