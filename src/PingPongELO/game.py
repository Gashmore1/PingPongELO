import time


class Game:
    #GAME_SCHEMA = [
    #    "player_number",
    #    "name",
    #    "game_id",
    #    "score",
    #    "time"
    #]

    def __init__(self, game_id: Optional[int], players: Optional[list[Players]], score: Optional[list[int]], time: Optional[float]):
        game_id: int = game_id

        if game_id:
            self.load_details()

        players: [Player] = players if players else []
        score: [int] = score if score else []
        time: float = time if time else 0.0

        if not (game_id or (players and score)):
            raise ValueError

    def get_game_id(self) -> int:
        return self.game_id

    def get_players(self) -> [Players]:
        return self.players

    def get_scores(self) -> [int]:
        return self.score

    def get_time(self) -> float:
        return self.time

    def load_details(self):
        self.get_players()
        self.get_scores()
        self.get_time()

    def save_details(self):
        pass
