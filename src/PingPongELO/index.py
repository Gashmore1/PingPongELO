from scoring import Scoring

from flask import redirect, render_template, stream_template, request, url_for, abort, Flask

import json

app = Flask(__name__)
with open("conf.json", "r") as f:
    pg_configuration = json.load(f)

scoring = Scoring(pg_configuration)

editing=False

@app.route("/")
def index():
    """Input form for new scores along with a leader board.""" 
    games = scoring.get_games(10)
    players = scoring.get_ratings()

    return stream_template("index.html", games=games, players=players, editing=editing)

@app.route("/result", methods=("GET", "POST"))
def create():
    """Save result."""
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

    if player_1 == "" or player_2 == "" or player_1 == player_2:
        return redirect(url_for("index"))

    ratings = scoring.add_game_result((player_1, player_2), (score_1, score_2))

    return redirect(url_for("index"))

@app.route("/edit/<id>")
def edit(id):
    return redirect(url_for("index"))

@app.route("/delete/<id>")
def delete(id):
    if id and editing:
        scoring.delete_game(int(id))

    return redirect(url_for("index"))

@app.route("/games")
@app.route("/games/<id>")
def game(id=None):
    if id:
        return redirect(url_for("index"))

    games = scoring.get_games()

    return stream_template("games.html", games=games, editing=editing)

@app.route("/players")
@app.route("/players/<name>")
def player(name=None):
    if name:
        return redirect(url_for("index"))

    players = scoring.get_ratings()

    return stream_template("players.html", players=players)

@app.route("/tournament")
def tournament():
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
