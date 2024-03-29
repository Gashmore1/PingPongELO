import pandas as pd
import psycopg2

from urllib.parse import quote_plus
from sqlalchemy import create_engine
import sqlalchemy
from sqlalchemy import text

import json

import time

import numpy as np

class Scoring:
    GAME_SCHEMA = [
        "player_number",
        "name",
        "game_id",
        "score",
        "time"
    ]

    RATING_SCHEMA = [
        "name",
        "rating",
        "game_id"
    ]

    def __init__(self, connection_conf):
        DB_USER_NAME = connection_conf["username"]
        DB_PASSWORD = quote_plus(connection_conf["password"])
        DB_URL = connection_conf["url"]
        DB_PORT = connection_conf["port"]
        DB_NAME = connection_conf["dbname"]
        self.DB_TABLES = connection_conf["table"]
        self.LEARNING_RATE = 20
        self.PROBABILITY_CORRECTION = 50

        self.engine = create_engine(f"postgresql+psycopg2://{DB_USER_NAME}:{DB_PASSWORD}@{DB_URL}:{DB_PORT}/{DB_NAME}")

    def get_players(self):
        with self.engine.connect() as conn:
            rating_data_frame = pd.read_sql(sql=f"select distinct name from {self.DB_TABLES["ratings"]}", con=conn, columns=self.RATING_SCHEMA)
        return rating_data_frame.name.values

    def get_player(self, name):
        with self.engine.connect() as conn:
            rating_data_frame = pd.read_sql(sql=f"select distinct name from {self.DB_TABLES["ratings"]} where name = '{name}'", con=conn, columns=self.RATING_SCHEMA)
        return rating_data_frame.name.values

    def get_ratings(self):
        with self.engine.connect() as conn:
            rating_data_frame = pd.read_sql(sql=f"select name, rating, game_id from {self.DB_TABLES["ratings"]}", con=conn, columns=self.RATING_SCHEMA)
        
        leader_board = rating_data_frame.sort_values("game_id", ascending=False).drop_duplicates(subset=["name"]).sort_values("rating", ascending=False)
        return leader_board

    def get_player_rating(self, name, game_id=None):
        with self.engine.connect() as conn:
            if game_id:
                rating_data_frame = pd.read_sql(
                    sql=f"select name, rating, game_id from {self.DB_TABLES["ratings"]} where name = '{name}' and game_id < {game_id} order by game_id desc limit 1",
                    con=conn,
                    columns=self.RATING_SCHEMA
                )
            else:
                rating_data_frame = pd.read_sql(
                    sql=f"select name, rating, game_id from {self.DB_TABLES["ratings"]} where name = '{name}' order by game_id desc limit 1",
                    con=conn,
                    columns=self.RATING_SCHEMA
                )
        
        if rating_data_frame.size == 0:
            return 100

        return rating_data_frame.rating.values[0]

    def calculate_ratings(self, game_id):
        list_of_new_games = sorted(list(self.__get_affected_games__(game_id)))
        for game in list_of_new_games:
            # Remove old rating
            with self.engine.connect() as conn:
                conn.execute(text(f"delete from {self.DB_TABLES["ratings"]} where game_id = {game}"))
                conn.commit()
            # Get game data
            game_data_frame = self.get_game(game)
            # Recalculate ratings

            names = game_data_frame.name.values
            rankings = [self.get_player_rating(name, game) for name in names]
            expected_result = 1/(1 + np.power(10,(rankings[1]-rankings[0])/self.PROBABILITY_CORRECTION))

            scores = game_data_frame.score.values

            result = max(scores)/sum(scores)

            if max(scores) == scores[0]:
                result = 1 - result

            player_a = rankings[0] + self.LEARNING_RATE * ((result) - (expected_result))
            player_b = rankings[1] + self.LEARNING_RATE * ((1-result) - (1-expected_result))

            rating_data_frame = pd.DataFrame([{"name": names[0],"rating": player_a,"game_id": game},{"name": names[1], "rating": player_b, "game_id": game}], columns=self.RATING_SCHEMA)
            # Add rating
            with self.engine.connect() as conn:
                rating_data_frame.to_sql(self.DB_TABLES["ratings"], con=conn, if_exists='append')

    def __get_affected_games__(self, game_id):
        # This needs reoptimising
        # This runs in O(2^n)
        # time which can be reduced with small number of players
        # some branches of games will already be considered by prior recurisions
        # Due to recurision limit only the last 9 games will be editable
        # (Python recursion limit 1000)
        # log_2(1000) > 9
        # Maybe Depth first would be better
        game_data_frame = self.get_game(game_id)
        affected_game_ids_set = set([game_id])

        for player in game_data_frame.name.values:
            with self.engine.connect() as conn:
                affected_games_data_frame = pd.read_sql(sql=f"select game_id from {self.DB_TABLES["games"]} where game_id > {game_id} and name = '{player}' order by game_id asc", con=conn, columns=self.GAME_SCHEMA)
            for game in list(affected_games_data_frame.game_id.values):
                affected_game_ids_set.update(self.__get_affected_games__(game))
 
        return affected_game_ids_set

    def get_game(self, game_id):
        with self.engine.connect() as conn:
            game_data_frame = pd.read_sql(sql=f"select * from {self.DB_TABLES["games"]} where game_id = {game_id}", con=conn, columns=self.GAME_SCHEMA)

        return game_data_frame

    def add_game_result(self, players, scores, play_time=time.time(), game_id=None):
        game_results = []
        result_pairings = zip(players, scores)

        if not game_id:
            game_id = self.get_latest_game_id() + 1
       
        for index, results in enumerate(result_pairings):
            player = results[0].strip()
            score = max([results[1], 0])
            game_results.append({"player_number": index, "name": player, "score": score, "game_id": game_id, "time": play_time})
        
        game_results_data_frame = pd.DataFrame(game_results, columns=self.GAME_SCHEMA)
        
        with self.engine.connect() as conn:
            game_results_data_frame.to_sql(self.DB_TABLES["games"], con=conn, if_exists='append')

        self.calculate_ratings(game_id)

    def edit_game(self, game_id, players, scores):
        # Delete game entry
        with self.engine.connect() as conn:
            play_time = pd.read_sql(sql=f"select time from {self.DB_TABLES["games"]} where game_id = {game_id}", con=conn, columns=self.GAME_SCHEMA).time.values[0]
        
        with self.engine.connect() as conn:
            conn.execute(text(f"delete from {self.DB_TABLES["games"]} where game_id = {game_id};"))
            conn.commit()
        # Write new entry
        self.add_game_result(players, scores, play_time=play_time, game_id=game_id)

    def delete_game(self, game_id):
        next_games = sorted(self.__get_affected_games__(game_id))[1:3]

        with self.engine.connect() as conn:
            conn.execute(text(f"delete from {self.DB_TABLES["games"]} where game_id = {game_id};"))
            conn.execute(text(f"delete from {self.DB_TABLES["ratings"]} where game_id = {game_id};"))
            conn.commit()

        for game in next_games:
            self.calculate_ratings(game)


        # Delete game entry
        # Recalculate based on next 2 game with depends on this game
        # If no prior game for either player treat them as a new player (This should be canonical)

    def get_latest_game_id(self):
        with self.engine.connect() as conn:
            game_data_frame = pd.read_sql(sql=f"select game_id from {self.DB_TABLES["games"]} order by game_id desc limit 1", con=conn, columns=self.GAME_SCHEMA)

        if game_data_frame.size == 0:
            return 0

        return game_data_frame.game_id.values[0]
    
