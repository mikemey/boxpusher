import arcade

from game_engine import BoxPusherEngine, Direction
from game_window import GameObserver, BoxPusherWindow


class AutoPlayer:
    def next_move(self, engine):
        pass


DEMO_LEVEL = {
    'field': (4, 4),
    'player': (1, 0),
    'walls': [],
    'boxes': [(2, 1)],
    'goal': (3, 3),
    'max_points': 20
}


class DemoPlayer(AutoPlayer):
    def __init__(self):
        self.move_ix = -1
        self.moves = [
            Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.RIGHT,
            Direction.UP, Direction.UP
        ]

    def next_move(self, engine):
        self.move_ix += 1
        engine.player_move(self.moves[self.move_ix])


class AutomaticMaster(GameObserver):
    def __init__(self, level=DEMO_LEVEL, player=DemoPlayer()):
        self.engine = BoxPusherEngine(level)
        self.player = player

    def start(self):
        window = BoxPusherWindow(self, interactive=False)
        window.reset_game(self.engine, "AI run")
        arcade.run()

    def game_done(self):
        arcade.close_window()

    def next_move(self):
        self.player.next_move(self.engine)


if __name__ == "__main__":
    AutomaticMaster().start()
