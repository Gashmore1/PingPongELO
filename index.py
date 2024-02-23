from pyspark.sql.types import FloatType, LongType, StructType, StructField, StringType, IntegerType
from pyspark.sql import SparkSession
from pyspark import SparkConf
from flask import redirect, render_template, request, url_for, abort, Flask
import json

# If this was ever to become GLICKO ranking method time since last game would need to be used
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def index():
    """Input form for new scores along with a leader board."""
    # Connection details will be in spark-sumbit command
    spark = SparkSession.builder.getOrCreate()  

    # Dataframe returned from spark
    players = [
        {
            "place": 1,
            "name": "Player1"
        },
        {
            "place": 2,
            "name": "Player2"
        }
    ]

    return render_template("index.html", players=players)


@app.route("/result", methods=("GET", "POST"))
def create():
    """Create a new post for the current user."""

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

    return redirect(url_for("index"))

if __name__ == "__main__":
  app.run(host="0.0.0.0", debug=True)