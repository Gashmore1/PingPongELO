import time
from urllib.parse import quote_plus

import pandas as pd
import psycopg2

from sqlalchemy import create_engine, text

import numpy as np

from pprint import pprint

import json

from scoring import Scoring

learning_rate = 20
probability_correction = 100

def result_expectation(old_ratings):
    ranking_difference = old_ratings[1] - old_ratings[0]
    return 1/(1+np.power(10,ranking_difference/probability_correction))

def score_from_rating(old_ratings, new_ratings):
    winning_score = 11

    expected_result = result_expectation(old_ratings)

    gain = np.array(old_ratings) - np.array(new_ratings) 

    winning_player = np.argmin(gain)

    result = expected_result + (new_ratings[winning_player] - old_ratings[winning_player])/learning_rate

    score = winning_score/result - winning_score

    losing_result = abs(min([round(score,0),11.0]))


    if winning_player == 0:
        return (11.0, losing_result)
    else:
        return (losing_result, 11.0)

def get_old_rating(player_details, df):
    name = player_details["name"]
    game_number = player_details["game_number"]
    df = df.drop(df[~((df.name == name) & (df.game_number == (game_number-1)))].index)

    if df.empty:
        return 100

    return df.rating.values[0]

schema = [
    "name",
    "rating",
    "game_id"
]

if __name__ == '__main__':
    old_table = "ratings"
    with open("conf.json", "r") as f:
        connection_conf = json.load(f)

    scoring = Scoring(connection_conf)

    db_user_name = connection_conf["username"]
    db_password = quote_plus(connection_conf["password"])
    db_url = connection_conf["url"]
    db_port = connection_conf["port"]
    db_name = connection_conf["dbname"]
    db_tables = connection_conf["table"]
    
    engine = create_engine(
        f"postgresql+psycopg2://{db_user_name}:{db_password}@{db_url}:{db_port}/{db_name}"
    )

    with engine.connect() as conn:
        rating_data_frame = pd.read_sql(
            sql=f"select * from {old_table}",
            con=conn,
            columns=schema
        )

    all_ratings = rating_data_frame.to_dict('records')

    for game_index in range(0,len(all_ratings),2):
        names = [all_ratings[game_index+i]["name"] for i in range(2)]
        new_ratings = [all_ratings[game_index+i]["rating"] for i in range(2)]
        old_ratings = [get_old_rating(all_ratings[game_index+i], rating_data_frame) for i in range(2)]

        #print(all_ratings[game_index], all_ratings[game_index+1])
        #print(old_ratings)
        #print()
        scores = score_from_rating(old_ratings, new_ratings)
        scoring.add_game_result(names, scores)

