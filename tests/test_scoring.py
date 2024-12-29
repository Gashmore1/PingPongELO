import json
from sqlalchemy import text

import pytest

from PingPongELO.scoring import Scoring

@pytest.fixture
def connect_to_database():
    with open("conf_test.json", "r") as f:
        config = json.load(f)
        database = Scoring(config)
    return database

@pytest.fixture
def reset_database(connect_to_database):
    with connect_to_database.engine.connect() as conn:
        conn.execute(text(f"delete from {connect_to_database.db_tables['ratings']}"))
        conn.execute(text(f"delete from {connect_to_database.db_tables['games']}"))
        conn.commit()

@pytest.fixture
def database(connect_to_database, reset_database):
    database = connect_to_database

    yield database

    reset_database

def test_get_no_players(database):
    # Test case, no players in database
    assert set(database.get_players()) == set()

def test_add_first_game(database):
    # Test case, one game with 2 unique players
    database.add_game_result(("Me","You"),(11,11))
    assert set(database.get_players()) == {"Me", "You"}

def test_add_second_game(database):
    # Test case, 2 games with 3 unique players
    database.add_game_result(("Me","You"),(11,11))
    database.add_game_result(("Me","Them"),(11,11))
    assert set(database.get_players()) == {"Me", "You", "Them"}

def test_elo_conservation(database):
    # Test case.
    # The number of points should be conserved
    database.add_game_result(("Me","You"),(11,0))
    ratings = list(database.get_ratings())
    number_of_players = len(ratings)
    total_score = sum(rating["rating"] for rating in ratings)
    expected_score = number_of_players * database.INITAL_RATING
    assert total_score == expected_score

def test_elo_growth(database):
    # Test case.
    # The number of points should be proportional to the number of players
    database.add_game_result(("Me","You"),(11,11))
    ratings = list(database.get_ratings())
    inital_total = sum(rating["rating"] for rating in ratings)
    database.add_game_result(("Me","Them"),(11,11))
    ratings = list(database.get_ratings())
    second_total = sum(rating["rating"] for rating in ratings)

    assert inital_total < second_total

def test_draw(database):
    # Test case, one game with 2 unique players
    database.add_game_result(("Me","You"),(11,11))
    players = list(database.get_ratings())
    assert players[0]["rating"] == players[1]["rating"]

def test_win(database):
    # Test case, one game with 2 unique players
    winner_name = "Me"
    loser_name = "You"

    database.add_game_result((winner_name,loser_name),(11,0))

    winner_rating = database.get_player_rating(winner_name)
    loser_rating = database.get_player_rating(loser_name)

    assert winner_rating > loser_rating

def test_edit_preserver_game_id(database):
    assert True

def test_edit_alter_ratings(database):
    assert True

def test_edit_alter_game_id(database):
    assert True

def test_edit_game(database):
    database.add_game_result(("Me","You"),(11,11))
    game_id = database.get_latest_game_id()
    database.edit_game(game_id, ("Me","You"),(11,0))
    new_game_id = database.get_latest_game_id()
    assert game_id == new_game_id
    ratings = list(database.get_ratings())
    assert ratings[0]["rating"] != ratings[1]["rating"]

    database.add_game_result(("Me","You"),(11,11))
    ratings = list(database.get_ratings())
    assert ratings[0]["rating"] != ratings[1]["rating"]

    database.edit_game(new_game_id, ("Me", "You"), (11,11))
    ratings = list(database.get_ratings())
    assert ratings[0]["rating"] == ratings[1]["rating"]

def test_delete_game(database):
    # Delete most recent Entry
    database.add_game_result(("Me","You"),(11,11))
    game_id = database.get_latest_game_id()
    database.delete_game(game_id)
    new_game_id = database.get_latest_game_id()
    assert new_game_id+1 == game_id
    # Delete game further down the tree
    database.add_game_result(("Me","You"), (11,0))
    first_game_id = database.get_latest_game_id()
    database.add_game_result(("Me", "Them"),(11,11))
    database.add_game_result(("You", "Her"),(11,11))
    ratings = list(database.get_ratings())
    ratings = [rating["rating"] for rating in ratings]
    assert ratings[0] != ratings[1]
    assert ratings[1] != ratings[2]
    assert ratings[2] != ratings[3]
    database.delete_game(first_game_id)
    ratings = list(database.get_ratings())
    ratings = [rating["rating"] for rating in ratings]
    assert ratings[0] == ratings[1]
    assert ratings[1] == ratings[2]
    assert ratings[2] == ratings[3]
