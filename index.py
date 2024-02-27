import pandas as pd
import psycopg2

from urllib.parse import quote_plus
from sqlalchemy import create_engine
import sqlalchemy

from flask import redirect, render_template, request, url_for, abort, Flask

import json
import numpy as np

from pprint import pprint

# If this was ever to become GLICKO ranking method time since last game would need to be used
from datetime import datetime

app = Flask(__name__)
LEARNING_RATE = 20
PROBABILITY_CORRECTION = 20

with open("conf.json", "r") as f:
    pg_configuration = json.load(f)

DB_USER_NAME = pg_configuration["username"]
DB_PASSWORD = quote_plus(pg_configuration["password"])
DB_URL = pg_configuration["url"]
DB_PORT = pg_configuration["port"]
DB_NAME = pg_configuration["dbname"]
DB_TABLE = pg_configuration["table"]

engine = create_engine(f"postgresql+psycopg2://{DB_USER_NAME}:{DB_PASSWORD}@{DB_URL}:{DB_PORT}/{DB_NAME}")

schema = [
    "name",
    "rating",
    "game_number"
    ]

def expected_result(ranking_a, ranking_b):
    expected_result_a = 1/(1 + np.power(10,(ranking_b-ranking_a)/PROBABILITY_CORRECTION))
    return expected_result_a

def new_rankings(ranking_a, ranking_b, change_rate, win):
    expected_result_a = expected_result(ranking_a, ranking_b)

    results = []

    results.append(ranking_a + change_rate * (win - expected_result_a))
    results.append(ranking_b + change_rate * ((1-win) - (1-expected_result_a)))

    return results

def get_player_score(name, df):
    if name in df.name:
        filter_name = df.name == name
        user_details = df.where(filter_name).sort_values("game_number", ascending=False).iloc[0]
        return user_details.rating
    else:
        return 100

def get_player_game_number(name, df):
    if name in df.name.values:
        filter_name = df.name == name
        user_details =  df.where(filter_name).sort_values("game_number", ascending=False).iloc[0]
        return user_details.game_number
    else:
        return 0


def add_player_score(name, rating, df):

    game_number = get_player_game_number(name, df) + 1


    return pd.DataFrame([{"name": name, "rating": float(rating), "game_number": game_number}], columns=schema)

def add_game_result(player_a, player_b, player_a_score, player_b_score, df):
    player_a_ranking = get_player_score(player_a, df)
    player_b_ranking = get_player_score(player_b, df)

    score_calculation = (max(player_a_score,player_b_score)/(player_a_score+player_b_score))

    if player_b_score == max(player_a_score,player_b_score):
        score_calculation = 1-score_calculation

    new_player_a_ranking, new_player_b_ranking = new_rankings(player_a_ranking, player_b_ranking, LEARNING_RATE, score_calculation)

    output_df = add_player_score(player_a, new_player_a_ranking, df)
    output_df.loc[len(output_df)] = add_player_score(player_b, new_player_b_ranking, df).iloc[0]

    return output_df

def leader_board(data):
    leader_board = data.sort_values("game_number", ascending=False).drop_duplicates(subset=["name"]).sort_values("rating", ascending=False)
    return [{"place": index+1, "name": leader_board.name.values[index]} for index in range(len(leader_board))]

@app.route("/")
def index():
    """Input form for new scores along with a leader board."""
    with engine.connect() as conn:
        try:
            ratings = pd.read_sql(sql=f"select name, rating, game_number from {DB_TABLE}", con=conn, columns=schema)
        except sqlalchemy.exc.ProgrammingError:
            ratings = pd.DataFrame([], columns=schema)

    # Dataframe returned from spark
    players = leader_board(ratings)

    return render_template("index.html", players=players)


@app.route("/result", methods=("GET", "POST"))
def create():
    """Save result."""
    with engine.connect() as conn:
        try:
            ratings = pd.read_sql(sql=f"select name, rating, game_number from {DB_TABLE}", con=conn, columns=schema)
        except sqlalchemy.exc.ProgrammingError:
            ratings = pd.DataFrame([], columns=schema)

    if request.method == 'POST':
        player_1 = request.form["player_1"]
        player_2 = request.form["player_2"]
        score_1 = request.form["score_1"]
        score_2 = request.form["score_2"]
    else:
        player_1 = request.args.get("player_1")
        player_2 = request.args.get("player_2")
        score_1 = request.args.get("score_1")
        score_2 = request.args.get("score_2")

    player_1 = player_1.strip()
    player_2 = player_2.strip()

    try:
        score_1 = max([int(score_1),0])
        score_2 = max([int(score_2),0])
    except Exception as e:
        return redirect(url_for("index"))

    if player_1 == "":
        return redirect(url_for("index"))

    if player_2 == "":
        return redirect(url_for("index"))


    #Use method to calculate score to append new scores
    ratings = add_game_result(player_1, player_2, score_1, score_2, ratings)

    with engine.connect() as conn:
        ratings.to_sql(DB_TABLE, con=conn, if_exists='append')

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0")