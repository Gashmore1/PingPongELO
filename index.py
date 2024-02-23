from pyspark.sql.types import DoubleType, LongType, StructType, StructField, StringType, IntegerType
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf

from flask import redirect, render_template, request, url_for, abort, Flask

import json
import numpy as np

# If this was ever to become GLICKO ranking method time since last game would need to be used
from datetime import datetime

app = Flask(__name__)
LEARNING_RATE = 50
TABLE = "pingpong.ratings"

with open("conf.json", "r") as f:
    configuration = json.load(f)

spark_conf = SparkConf().setAll(configuration)

def expected_result(ranking_a, ranking_b):
    expected_result_a = 1/(1 + np.power(10,(ranking_b-ranking_a)/100))
    return expected_result_a

def new_rankings(ranking_a, ranking_b, change_rate, win):
    expected_result_a = expected_result(ranking_a, ranking_b)

    results = []

    results.append(ranking_a + change_rate * (win - expected_result_a))
    results.append(ranking_b + change_rate * ((1-win) - (1-expected_result_a)))

    return results

def get_player_score(name, df):
    user_details = df.where(df.name == name).sort(df.game_number, ascending=False).first()
    if user_details:
        return user_details.rating
    else:
        return 100

def get_player_game_number(name, df):
    user_details =  df.where(df.name == name).sort(df.game_number, ascending=False).first()
    if user_details:
        return user_details.game_number
    else:
        return 0


def add_player_score(name, rating, df, session):
    schema = StructType([
        StructField("name", StringType(), False),
        StructField("rating", DoubleType(), False),
        StructField("game_number", IntegerType(), False)]
        )

    game_number = get_player_game_number(name, df) + 1

    df = df.unionAll(session.createDataFrame([{"name": name, "rating": float(rating), "game_number": game_number}], schema=schema))
    return df

def add_game_result(player_a, player_b, player_a_score, player_b_score, df, session):
    player_a_ranking = get_player_score(player_a, df)
    player_b_ranking = get_player_score(player_b, df)

    score_calculation = (max(player_a_score,player_b_score)/(player_a_score+player_b_score))

    if player_b_score == max(player_a_score,player_b_score):
        score_calculation = 1-score_calculation

    new_player_a_ranking, new_player_b_ranking = new_rankings(player_a_ranking, player_b_ranking, LEARNING_RATE, score_calculation)

    df = add_player_score(player_a, new_player_a_ranking, df, session)
    df = add_player_score(player_b, new_player_b_ranking, df, session)

    return df

def leader_board(data):
    leader_board = data.select(data.name, data.rating, data.game_number).sort(data.game_number, ascending=False).dropDuplicates(["name"]).sort(data.rating, ascending=False).collect()
    return [{"place": index, "name": player.name} for index, player in enumerate(leader_board)]

@app.route("/")
def index():
    spark = SparkSession.builder.appName("PingPongELO").config(conf=spark_conf).getOrCreate()
    """Input form for new scores along with a leader board."""
    # Connection details will be in spark-sumbit command
    table_exists = spark.catalog.tableExists(TABLE)

    if table_exists:
        ratings = spark.read.table(TABLE)
    else:
        schema = StructType([
            StructField("name", StringType(), False),
            StructField("rating", DoubleType(), False),
            StructField("game_number", IntegerType(), False)
            ]
        )
        ratings = spark.createDataFrame([],schema=schema)

    # Dataframe returned from spark
    players = leader_board(ratings)

    spark.stop()

    return render_template("index.html", players=players)


@app.route("/result", methods=("GET", "POST"))
def create():
    """Save result."""
    spark = SparkSession.builder.appName("PingPongELO").config(conf=spark_conf).getOrCreate()

    # Connection details will be in spark-sumbit command
    table_exists = spark.catalog.tableExists(TABLE)

    if table_exists:
        ratings = spark.read.table(TABLE)
    else:
        schema = StructType([
            StructField("name", StringType(), False),
            StructField("rating", DoubleType(), False),
            StructField("game_number", IntegerType(), False)
            ]
        )
        ratings = spark.createDataFrame([],schema=schema)

    if request.method == 'POST':
        player_1 = request.form["player_1"]
        player_2 = request.form["player_2"]
        score_1 = int(request.form["score_1"])
        score_2 = int(request.form["score_2"])
    else:
        player_1 = request.args.get("player_1")
        player_2 = request.args.get("player_2")
        score_1 = int(request.args.get("score_1"))
        score_2 = int(request.args.get("score_2"))

    #Use method to calculate score to append new scores
    scores = add_game_result(player_1, player_2, score_1, score_2, ratings, spark)

    print(scores.collect())

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)