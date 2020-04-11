import numpy as np
import pyglet
from pyglet.window import key

from racer_engine import RacerEngine, PlayerOperation, CAR_BOUND_POINTS
from tracks import OUTER_TRACK, INNER_TRACK, WINDOW_SIZE

pyglet.resource.path = ['resources']
pyglet.resource.reindex()
car_frame_img = pyglet.resource.image('car-frame.png')
car_frame_img.anchor_x = car_frame_img.width * 2 / 5
car_frame_img.anchor_y = car_frame_img.height / 2


def convert_data(points, color, color_mode='c3B'):
    pts_count = int(len(points) / 2)
    vertices = ('v2i', points)
    color_data = (color_mode, color * pts_count)
    return pts_count, vertices, color_data


def create_vertex_list(points, color):
    return pyglet.graphics.vertex_list(*convert_data(points, color))


def add_points_to(batch, points, color, mode=pyglet.gl.GL_LINE_STRIP, group=None):
    pts_count, vertices, color_data = convert_data(points, color)
    batch.add(pts_count, mode, group, vertices, color_data)


class RacerWindow(pyglet.window.Window):
    BG_COLOR = 0.5, 0.8, 0.4, 1
    WINDOW_POS = 20, 0
    TRACK_COLOR = 160, 10, 60
    CAR_COLOR = tuple(np.random.randint(0, 255, size=3))

    def __init__(self, engine: RacerEngine):
        super().__init__(*WINDOW_SIZE, caption='Racer')
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.set_location(*self.WINDOW_POS)
        pyglet.gl.glClearColor(*self.BG_COLOR)
        self.engine = engine
        self.batch = pyglet.graphics.Batch()
        add_points_to(self.batch, OUTER_TRACK, self.TRACK_COLOR)
        add_points_to(self.batch, INNER_TRACK, self.TRACK_COLOR)

        self.score_box = ScoreBox(self.batch)
        self.car_frame = pyglet.sprite.Sprite(img=car_frame_img, batch=self.batch)
        self.car_frame.scale = 0.5
        self.car_color = create_vertex_list(CAR_BOUND_POINTS, self.CAR_COLOR)
        self.pause_overlay = GameOverlay('Paused', '"p" to continue...')
        self.lost_overlay = GameOverlay('Lost!', '')

        self.player_operations = PlayerOperation()
        self.game_state = GameState()

    def on_draw(self):
        self.clear()
        self.draw_car_background()
        pyglet.gl.glLineWidth(5)
        self.batch.draw()
        if self.game_state.is_paused:
            self.pause_overlay.draw()
        if self.game_state.lost:
            self.lost_overlay.draw()

    def draw_car_background(self):
        pyglet.gl.glPushMatrix()

        pyglet.gl.glTranslatef(self.car_frame.x, self.car_frame.y, 0)
        pyglet.gl.glRotatef(-self.car_frame.rotation, 0, 0, 1.0)
        self.car_color.draw(pyglet.gl.GL_POLYGON)
        pyglet.gl.glPopMatrix()

    def on_key_press(self, symbol, modifiers):
        super().on_key_press(symbol, modifiers)
        if self.engine.game_over:
            return
        if symbol == key.P:
            self.game_state.is_paused = not self.game_state.is_paused
        if symbol == key.UP:
            self.player_operations.accelerate()
        if symbol == key.DOWN:
            self.player_operations.reverse()
        if symbol == key.LEFT:
            self.player_operations.turn_left()
        if symbol == key.RIGHT:
            self.player_operations.turn_right()

    def on_key_release(self, symbol, modifiers):
        if symbol in (key.UP, key.DOWN):
            self.player_operations.stop_direction()
        if symbol == key.LEFT:
            self.player_operations.stop_left()
        if symbol == key.RIGHT:
            self.player_operations.stop_right()

    def on_deactivate(self):
        self.game_state.is_paused = True

    def update(self, dt):
        if self.game_state.is_paused:
            return
        self.engine.update(dt, self.player_operations)
        if self.engine.game_over:
            self.game_state.lost = True
            return
        pl = self.engine.player
        self.car_frame.update(x=pl.position[0], y=pl.position[1], rotation=pl.rotation)
        self.score_box.update_text(self.engine.score)


class GameState:
    def __init__(self):
        self.is_paused = False
        self.lost = False


class GameOverlay:
    BG_COLOR = 30, 30, 30, 150
    MAIN_COLOR = 255, 255, 0, 255
    SECOND_COLOR = 255, 255, 150, 255

    def __init__(self, main_txt, support_txt, exit_txt='"Esc" to quit'):
        self.overlay = pyglet.graphics.Batch()
        background = pyglet.graphics.OrderedGroup(0)
        foreground = pyglet.graphics.OrderedGroup(1)

        size = WINDOW_SIZE
        cnt, vertices, transparent = convert_data(
            [0, 0, size[0], 0, size[0], size[1], 0, size[1]],
            self.BG_COLOR, color_mode='c4B')
        self.overlay.add(4, pyglet.gl.GL_POLYGON, background, vertices, transparent)

        main_lbl = pyglet.text.Label(main_txt, batch=self.overlay, group=foreground,
                                     color=self.MAIN_COLOR, font_size=22, bold=True)
        main_lbl.x = size[0] / 2 - main_lbl.content_width / 2
        main_lbl.y = size[1] / 2 - main_lbl.content_height / 2
        support_lbl = pyglet.text.Label(support_txt, batch=self.overlay, group=foreground,
                                        color=self.SECOND_COLOR, font_size=16)
        support_lbl.x = size[0] / 2 - support_lbl.content_width / 2
        support_lbl.y = size[1] / 2 - main_lbl.content_height - support_lbl.content_height
        exit_lbl = pyglet.text.Label(exit_txt, batch=self.overlay, group=foreground,
                                     color=self.SECOND_COLOR, font_size=16)
        exit_lbl.x = size[0] / 2 - exit_lbl.content_width / 2
        exit_lbl.y = size[1] / 2 - main_lbl.content_height - exit_lbl.content_height * 2.3

    def draw(self):
        self.overlay.draw()


class ScoreBox:
    BG_COLOR = 50, 50, 200
    SCORE_BOX = 125, 40

    def __init__(self, batch):
        offset = np.array(WINDOW_SIZE) - self.SCORE_BOX
        box = np.append(offset, offset + self.SCORE_BOX)
        self.center_x = offset[0] + self.SCORE_BOX[0] / 2

        background = pyglet.graphics.OrderedGroup(0)
        foreground = pyglet.graphics.OrderedGroup(1)
        add_points_to(batch, [
            box[0], box[1], box[2], box[1], box[2], box[3], box[0], box[3], box[0], box[1]
        ], self.BG_COLOR, pyglet.gl.GL_POLYGON, background)
        self.label = pyglet.text.Label(x=WINDOW_SIZE[0] - 100, y=WINDOW_SIZE[1] - 25, batch=batch, group=foreground)

    def update_text(self, score):
        self.label.text = 'Score: {}'.format(score)
        self.label.x = self.center_x - self.label.content_width / 2


if __name__ == '__main__':
    w = RacerWindow(RacerEngine())
    pyglet.clock.schedule_interval(w.update, 1 / 120.0)
    pyglet.app.run()
