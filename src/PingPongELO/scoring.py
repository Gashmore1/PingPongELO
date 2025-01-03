
import time
from urllib.parse import quote_plus

import pandas as pd
import psycopg2

from sqlalchemy import create_engine, text

import numpy as np

from tqdm import tqdm
from pprint import pprint

class Scoring:
    INITAL_RATING = 100

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

    time_approximations = {
        "Now": 0,
        "~Minute ago": 3 * 60,
        "~Hour ago": 60 * 60,
        "~Day ago": 24 * 60 * 60,
        "~Week ago": 7 * 24 * 60 * 60,
        "In a galaxy far, far away...": 2 * 7 * 24 * 60 * 60
    }

    def __init__(self, connection_conf):
        db_user_name = connection_conf["username"]
        db_password = quote_plus(connection_conf["password"])
        db_url = connection_conf["url"]
        db_port = connection_conf["port"]
        db_name = connection_conf["dbname"]
        self.db_tables = connection_conf["table"]
        self.learning_rate = 20
        self.probability_correction = 50

        self.engine = create_engine(
            f"postgresql+psycopg2://{db_user_name}:{db_password}@{db_url}:{db_port}/{db_name}"
        )

    def get_players(self):
        with self.engine.connect() as conn:
            rating_data_frame = pd.read_sql(
                sql=f"select distinct name from {self.db_tables['ratings']}",
                con=conn,

                columns=self.RATING_SCHEMA
            )
        return rating_data_frame.name.values

    def get_player(self, name):
        with self.engine.connect() as conn:
            rating_data_frame = pd.read_sql(
                sql=f"select name, game_id from {self.db_tables['ratings']} where name = '{name}'",
                con=conn,
                columns=self.RATING_SCHEMA
            )
            rating_data_frame = rating_data_frame\
            .drop(
                rating_data_frame[~(rating_data_frame.name == name)].index
            )\
            .to_dict("records")

        return rating_data_frame

    def is_stale(self,player):
        age = self.age(self.get_game(player["game_id"]).head(1).time.values[0])

        if age < 4 * list(self.time_approximations.values())[-1]:
            return True
        else:
            return False

    def get_ratings(self):
        with self.engine.connect() as conn:
            rating_data_frame = pd.read_sql(
                sql=f"select name, rating, game_id from {self.db_tables['ratings']}",
                con=conn,
                columns=self.RATING_SCHEMA
            )
        leader_board = rating_data_frame\
        .sort_values("game_id", ascending=False)\
        .drop_duplicates(subset=["name"])\
        .sort_values("rating", ascending=False)\
        .to_dict('records')

        leader_board = list(filter(self.is_stale, leader_board))

        for index, player in enumerate(leader_board):
            leader_board[index]["rating"] = round(leader_board[index]["rating"], 1)
            leader_board[index]["ranking"] = index+1

        return leader_board

    def get_player_rating(self, name, game_id=None):
        with self.engine.connect() as conn:
            if game_id:
                rating_data_frame = pd.read_sql(
                    sql=f"select name, rating, game_id from {self.db_tables['ratings']}",
                    con=conn,
                    columns=self.RATING_SCHEMA
                )

                rating_data_frame = rating_data_frame\
                .drop(
                    rating_data_frame
                    [
                        ~(
                        (rating_data_frame.name == name) &
                        (rating_data_frame.game_id < game_id)
                        )
                    ]\
                    .index
                )\
                .sort_values("game_id", ascending=False)\
                .head(1)

            else:
                rating_data_frame = pd.read_sql(
                    sql=f"select name, rating, game_id from {self.db_tables['ratings']}",
                    con=conn,
                    columns=self.RATING_SCHEMA
                )

                rating_data_frame = rating_data_frame\
                .drop(rating_data_frame[~(rating_data_frame.name == name)].index)\
                .sort_values("game_id", ascending=False)\
                .head(1)

        if rating_data_frame.empty:
            return self.INITAL_RATING

        return rating_data_frame.rating.values[0]

    def calculate_ratings(self, game_id):
        print(game_id)
        list_of_new_games = sorted(list(self.__get_affected_games__(game_id))) 
        print(len(list_of_new_games))

        for game in tqdm(list_of_new_games):
            # Remove old rating
            with self.engine.connect() as conn:
                conn.execute(
                    text(f"delete from {self.db_tables['ratings']} where game_id = {game}")
                )
                conn.commit()
            # Get game data
            game_data_frame = self.get_game(game)
            # Recalculate ratings

            names = game_data_frame.name.values
            rankings = [self.get_player_rating(name, game) for name in names]
            ranking_difference = rankings[1]-rankings[0]
            expected_result = 1/(1 + np.power(10,ranking_difference/self.probability_correction))

            scores = game_data_frame.score.values

            result = max(scores)/sum(scores)

            if max(scores) == scores[1]:
                result = 1 - result

            player_a = rankings[0] + self.learning_rate * ((result) - (expected_result))
            player_b = rankings[1] + self.learning_rate * ((1-result) - (1-expected_result))

            rating_data_frame = pd.DataFrame(
                [
                    {"name": names[0],"rating": player_a,"game_id": game},
                    {"name": names[1], "rating": player_b, "game_id": game}
                ],
                columns=self.RATING_SCHEMA
            )
            # Add rating
            with self.engine.connect() as conn:
                rating_data_frame.to_sql(self.db_tables["ratings"], con=conn, if_exists='append')

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

        with self.engine.connect() as conn:
            affected_games_data_frame = pd.read_sql(
                sql=f"select name, game_id from {self.db_tables['games']}",
                con=conn,
                columns=self.GAME_SCHEMA
            )

            affected_games_data_frame = affected_games_data_frame\
            .drop(
                affected_games_data_frame
                [
                ~(affected_games_data_frame.game_id > game_id)
                ]
                .index
            )\
            .sort_values("game_id", ascending=True)

        affected_game_ids_set.update(affected_games_data_frame.game_id.values)
            #for game in list(affected_games_data_frame.game_id.values):
            #    affected_game_ids_set.update(self.__get_affected_games__(game))

        return affected_game_ids_set

    def get_games(self, limit=None, start_id=None):
        with self.engine.connect() as conn:
            games_data_frame = pd.read_sql(
                sql=f"select * from {self.db_tables['games']}",
                con=conn,
                columns=self.GAME_SCHEMA
            )\
            .sort_values(
                "game_id", ascending=False
            )

            if start_id:
                games_data_frame = games_data_frame\
                .drop(game_data_frame[~(game_data_frame.game_id <= start_id)].index)

            if limit:
                games_data_frame = games_data_frame.head(2*limit) 

            games_data_frame = games_data_frame.to_dict('records')

            games = []

            for game_index in range(0, len(games_data_frame), 2):
                current_time = time.time()
                game_time = games_data_frame[game_index]["time"]
                
                age = self.age(game_time)

                time_increments =  np.array(list(self.time_approximations.values()))

                time_distances = np.abs(time_increments - age)

                time_closest = np.argmin(time_distances)

                time_comment = list(self.time_approximations.keys())[time_closest]

                games_data_frame[game_index]["time"] = time_comment
                games_data_frame[game_index+1]["time"] = time_comment

                games.append(
                    [games_data_frame[game_index], games_data_frame[game_index+1]]
                )

            return games

    def age(self, play_time):
        current_time = time.time()
        return current_time - play_time

    def get_game(self, game_id):
        with self.engine.connect() as conn:
            game_data_frame = pd.read_sql(
                sql=f"select * from {self.db_tables['games']} where game_id = {game_id}",
                con=conn,
                columns=self.GAME_SCHEMA
            )

        return game_data_frame

    def add_game_result(self, players, scores, play_time=None, game_id=None):
        game_results = []
        result_pairings = zip(players, scores)

        if not play_time:
            play_time = time.time()

        if not game_id:
            game_id = self.get_latest_game_id() + 1

        for index, results in enumerate(result_pairings):
            player = results[0].strip()
            score = max([results[1], 0])
            game_results.append(
                {
                    "player_number": index,
                    "name": player,
                    "score": score,
                    "game_id": game_id,
                    "time": play_time
                }
            )

        game_results_data_frame = pd.DataFrame(game_results, columns=self.GAME_SCHEMA)

        with self.engine.connect() as conn:
            game_results_data_frame.to_sql(self.db_tables["games"], con=conn, if_exists='append')

        self.calculate_ratings(game_id)

    def edit_game(self, game_id, players, scores):
        # Delete game entry
        with self.engine.connect() as conn:
            play_time = pd.read_sql(
                sql=f"select time, game_id from {self.db_tables['games']}",
                con=conn,
                columns=self.GAME_SCHEMA
            )

            play_time = play_time\
            .drop(play_time[~(play_time.game_id == game_id)].index)\
            .time\
            .values[0]

        with self.engine.connect() as conn:
            conn.execute(
                text(f"delete from {self.db_tables['games']} where game_id = {game_id}")
            )
            conn.execute(
                text(f"delete from {self.db_tables['ratings']} where game_id = {game_id}")
            )
            conn.commit()
        # Write new entry
        self.add_game_result(players, scores, play_time=play_time, game_id=game_id)

    def delete_game(self, game_id):
        next_games = sorted(self.__get_affected_games__(game_id))[1:3]

        with self.engine.connect() as conn:
            conn.execute(
                text(f"delete from {self.db_tables['games']} where game_id = {game_id};")
            )
            conn.execute(
                text(f"delete from {self.db_tables['ratings']} where game_id = {game_id};")
            )
            conn.commit()

        for game in next_games:
            self.calculate_ratings(game)


        # Delete game entry
        # Recalculate based on next 2 game with depends on this game
        # If no prior game for either player treat them as a new player (This should be canonical)

    def get_latest_game_id(self):
        with self.engine.connect() as conn:
            game_data_frame = pd.read_sql(
                sql=f"select game_id from {self.db_tables['games']} order by game_id desc limit 1",
                con=conn,
                columns=self.GAME_SCHEMA
            )

        if game_data_frame.size == 0:
            return 0

        return game_data_frame.game_id.values[0]

    def get_players_last_game(self, name):
        with self.engine.connect() as conn:
            game_data_frame = pd.read_sql(
                sql=f"select game_id, player_number, name, score, time from {self.db_tables['games']}",
                con=conn,
                columns=self.GAME_SCHEMA
            )

        game_data_frame = game_data_frame\
        .drop(
            game_data_frame
                [
                    ~(
                        (game_data_frame.name == name)
                    )
                ]
                .index
            ).sort_values("game_id", ascending=False)\
            .head(1)\
            .to_dict('records')

        return game_data_frame

if __name__ == "__main__":
    import json
    with open("conf.json", "r") as f:
        pg_configuration = json.load(f)

    game = Scoring(pg_configuration)

    pprint(game.get_ratings())
