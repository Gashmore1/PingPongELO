class Player:
    #RATING_SCHEMA = [
    #    "name",
    #    "rating",
    #    "game_id"
    #]

    def __init__(self, name: str, connection):
        name: str = name
        games: set[Games] = set()
        rating: float = 100.0

    def get_games(self) -> set[Game]:
        self.games = self.populate_games()
        return self.games

    def get_rating(self) -> float:
        return self.rating

    def get_last_game(self) -> Game:
        last_game = sorted(self.get_games())[0]
        return last_game

    def populate_games(self, limit: Optional[int]):
        pass

    def load_details(self):
        pass

    def save_details(self):
        pass
