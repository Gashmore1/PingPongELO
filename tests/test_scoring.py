import unittest

import json
from sqlalchemy import text

from scoring import Scoring


class TestScore(unittest.TestCase):

    with open("conf.json", "r") as f:
        config = json.load(f)
        db = Scoring(config)

    def setUp(self):
        with self.db.engine.connect() as conn:
            conn.execute(text(f"delete from {self.db.DB_TABLES["ratings"]}"))
            conn.execute(text(f"delete from {self.db.DB_TABLES["games"]}"))
            conn.commit()


    def test_get_player(self):
        self.assertEqual(list(self.db.get_players()), [])
        self.db.add_game_result(("Me","You"),(11,11))
        self.assertEqual(len(self.db.get_players()), 2)
        self.db.add_game_result(("Me","Them"),(11,11))
        self.assertEqual(len(self.db.get_players()), 3)

    def test_add_game(self):
        self.db.add_game_result(("Me","You"),(11,11))
        self.assertEqual(list(self.db.get_players()), ["Me", "You"])
        ratings = list(self.db.get_ratings().rating.values)
        self.assertEqual(sum(ratings), 200)
        rating_difference = ratings[0] - ratings[1]
        self.assertEqual(rating_difference, 0)
        # Test that the winner gains points

    def test_edit_game(self):
        self.db.add_game_result(("Me","You"),(11,11))
        game_id = self.db.get_latest_game_id()
        self.db.edit_game(game_id, ("Me","You"),(11,0))
        new_game_id = self.db.get_latest_game_id()
        self.assertEqual(game_id, new_game_id)
        ratings = list(self.db.get_ratings().rating.values)
        self.assertNotEqual(ratings[0],ratings[1])

        self.db.add_game_result(("Me","You"),(11,11))
        ratings = list(self.db.get_ratings().rating.values)
        self.assertNotEqual(ratings[0],ratings[1])
        self.db.edit_game(new_game_id, ("Me", "You"), (11,11))
        ratings = list(self.db.get_ratings().rating.values)
        self.assertEqual(ratings[0],ratings[1])

    def test_delete_game(self):
        # Delete most recent Entry
        self.db.add_game_result(("Me","You"),(11,11))
        game_id = self.db.get_latest_game_id()
        self.db.delete_game(game_id)
        new_game_id = self.db.get_latest_game_id()
        self.assertEqual(new_game_id+1, game_id)
        # Delete game further down the tree
        self.db.add_game_result(("Me","You"), (11,0))
        first_game_id = self.db.get_latest_game_id()
        self.db.add_game_result(("Me", "Them"),(11,11))
        self.db.add_game_result(("You", "Her"),(11,11))
        ratings = list(self.db.get_ratings().rating.values)
        self.assertNotEqual(ratings[0], ratings[1])
        self.assertNotEqual(ratings[1], ratings[2])
        self.assertNotEqual(ratings[2], ratings[3])
        self.db.delete_game(first_game_id)
        ratings = list(self.db.get_ratings().rating.values)
        self.assertEqual(ratings[0], ratings[1])
        self.assertEqual(ratings[1], ratings[2])
        self.assertEqual(ratings[2], ratings[3])

if __name__ == '__main__':
    unittest.main()
