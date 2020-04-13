from typing import Tuple, List

from pyglet.window import key

from game.racer_engine import RacerEngine, PlayerOperation
from game.racer_window import RaceController
from game.racer_window import RacerWindow


class ManualMaster:
    def __init__(self, two_players=False):
        self.controller = ManualController(two_players)

    def run(self):
        w = RacerWindow(self.controller)
        w.start()


PLAYER1_KEYS = key.UP, key.DOWN, key.LEFT, key.RIGHT
PLAYER2_KEYS = key.W, key.S, key.A, key.D


class ManualController(RaceController):
    def __init__(self, two_players: bool):
        super().__init__()
        self.two_players = two_players
        self.players = [ManualPlayer(*PLAYER1_KEYS)]
        if self.two_players:
            self.players.append(ManualPlayer(*PLAYER2_KEYS))

    def get_player_count(self):
        return len(self.players)

    def reset(self):
        super().reset()
        self.players = [ManualPlayer(*PLAYER1_KEYS)]
        if self.two_players:
            self.players.append(ManualPlayer(*PLAYER2_KEYS))

    def on_key_press(self, symbol):
        if self.show_lost_screen:
            if symbol == key.N:
                self.reset()
            return
        if symbol == key.P:
            self.show_paused_screen = not self.show_paused_screen
        for player in self.players:
            player.on_key_press(symbol)

    def on_key_release(self, symbol):
        for player in self.players:
            player.on_key_release(symbol)

    def focus_lost(self):
        self.show_paused_screen = True

    def get_score_text(self):
        if self.two_players:
            if self.players[0].score > self.players[1].score:
                return 'Player 1'
            else:
                return 'Player 2'
        return 'Score: {:.0f}'.format(self.players[0].score)

    def update_players(self, dt) -> List[Tuple[float, float, float]]:
        if not (self.show_paused_screen or self.show_lost_screen):
            for player in self.players:
                player.update(dt)

            if all([player.engine.game_over for player in self.players]):
                self.show_lost_screen = True
        return [player.get_position() for player in self.players]


class ManualPlayer:
    def __init__(self, up, down, left, right):
        self.score = 0
        self.engine = RacerEngine()
        self.operation = PlayerOperation()
        self.up, self.down, self.left, self.right = up, down, left, right

    def reset(self):
        self.score = 0
        self.engine = RacerEngine()
        self.operation = PlayerOperation()

    def on_key_press(self, symbol):
        if symbol == self.up:
            self.operation.accelerate()
        if symbol == self.down:
            self.operation.reverse()
        if symbol == self.left:
            self.operation.turn_left()
        if symbol == self.right:
            self.operation.turn_right()

    def on_key_release(self, symbol):
        if symbol in (self.up, self.down):
            self.operation.stop_direction()
        if symbol == self.left:
            self.operation.stop_left()
        if symbol == self.right:
            self.operation.stop_right()

    def update(self, dt) -> List[Tuple[float, float, float]]:
        if not self.engine.game_over:
            self.engine.update(dt, self.operation)
            relevant_speed = self.engine.player.relevant_speed
            amp = 0.002 if relevant_speed < 0 else 0.001
            self.score += relevant_speed * amp

    def get_position(self):
        return self.engine.player.position[0], \
               self.engine.player.position[1], \
               self.engine.player.rotation
