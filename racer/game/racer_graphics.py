from os import path

import numpy as np
import pyglet

from .racer_engine import PlayerState, CAR_BOUND_POINTS
from .tracers import get_trace_points
from .tracks import OUTER_TRACK, INNER_TRACK, TRACK_SIZE

resource_dir = path.join(path.abspath(path.dirname(__file__)), 'resources')
pyglet.resource.path = [resource_dir]
pyglet.resource.reindex()
car_frame_img = pyglet.resource.image('car-frame.png')
car_frame_img.anchor_x = car_frame_img.width / 3
car_frame_img.anchor_y = car_frame_img.height / 2


def random_color():
    return tuple(np.random.randint(0, 255, size=3))


def convert_data(points, color=None, color_mode='c3B'):
    pts_count = int(len(points) / 2)
    vertices = ('v2i', points)
    color_data = (color_mode, color * pts_count) if color else None
    return pts_count, vertices, color_data


def add_points_to(batch, points, color, mode=pyglet.gl.GL_LINE_STRIP, group=None):
    pts_count, vertices, color_data = convert_data(points, color)
    batch.add(pts_count, mode, group, vertices, color_data)


class GraphicsElement:
    def __init__(self):
        self.batch = pyglet.graphics.Batch()

    def draw(self):
        self.batch.draw()


class CarGraphics(GraphicsElement):
    TRACE_COLOR = 100, 100, 255

    def __init__(self, show_traces=True):
        super().__init__()
        self.show_traces = show_traces
        self.car_frame = pyglet.sprite.Sprite(img=car_frame_img, batch=self.batch)
        self.car_frame.scale = 0.5
        pts, vertices, _ = convert_data(CAR_BOUND_POINTS)
        color_data = 'c3B', random_color() + random_color() + random_color() + random_color()
        self.car_color = pyglet.graphics.vertex_list(pts, vertices, vertices, color_data)

    def draw(self):
        if self.show_traces:
            self.draw_traces()
        pyglet.gl.glPushMatrix()
        pyglet.gl.glTranslatef(self.car_frame.x, self.car_frame.y, 0)
        pyglet.gl.glRotatef(-self.car_frame.rotation, 0, 0, 1.0)
        self.car_color.draw(pyglet.gl.GL_POLYGON)
        pyglet.gl.glPopMatrix()
        self.batch.draw()

    def draw_traces(self):
        pyglet.gl.glLineWidth(1)
        for pos in get_trace_points(self.car_frame.position, self.car_frame.rotation):
            pyglet.graphics.draw(2, pyglet.gl.GL_LINE_STRIP,
                                 ('v2f', self.car_frame.position + pos),
                                 ('c3B', self.TRACE_COLOR * 2)
                                 )

    def update(self, player: PlayerState):
        self.car_frame.update(x=player.position[0], y=player.position[1], rotation=player.rotation)


class TrackGraphics(GraphicsElement):
    TRACK_COLOR = 160, 10, 60

    def __init__(self):
        super().__init__()
        add_points_to(self.batch, OUTER_TRACK, self.TRACK_COLOR)
        add_points_to(self.batch, INNER_TRACK, self.TRACK_COLOR)

    def draw(self):
        pyglet.gl.glLineWidth(5)
        self.batch.draw()


class WarmupSequence:
    def __init__(self):
        self.__overlays = [(GameOverlay('3', ''), 1.0), (GameOverlay('2', ''), 1.0),
                           (GameOverlay('1', ''), 1.0), (GameOverlay('', 'GO !!!', '', text_only=True), 0.7)]
        self.__current_ix = -1

    def reset(self):
        self.__current_ix = -1

    def __next__(self):
        self.__current_ix += 1
        return self.__is_current_ix_valid()

    def current_delay(self):
        return self.__overlays[self.__current_ix][1]

    def draw(self):
        if self.__is_current_ix_valid():
            self.__overlays[self.__current_ix][0].draw()

    def shows_last_screen(self):
        return self.__current_ix == len(self.__overlays) - 1

    def __is_current_ix_valid(self):
        return 0 <= self.__current_ix < len(self.__overlays)


class GameOverlay(GraphicsElement):
    REGULAR_COLORS = [(255, 255, 0, 255), (255, 255, 150, 255), (30, 30, 30, 150)]
    TEXT_ONLY_COLORS = [(60, 60, 60, 255), (60, 60, 60, 255), (0, 0, 0, 0)]

    def __init__(self, main_txt, support_txt, exit_txt='"Esc" to quit', text_only=False):
        super().__init__()
        colors = self.TEXT_ONLY_COLORS if text_only else self.REGULAR_COLORS
        background = pyglet.graphics.OrderedGroup(0)
        cnt, vertices, transparent = convert_data(
            [0, 0, TRACK_SIZE[0], 0, TRACK_SIZE[0], TRACK_SIZE[1], 0, TRACK_SIZE[1]],
            colors[2], color_mode='c4B')
        self.batch.add(4, pyglet.gl.GL_POLYGON, background, vertices, transparent)

        foreground = pyglet.graphics.OrderedGroup(1)
        main_lbl = pyglet.text.Label(main_txt, batch=self.batch, group=foreground,
                                     color=colors[0], font_size=22, bold=True)
        main_lbl.x = TRACK_SIZE[0] / 2 - main_lbl.content_width / 2
        main_lbl.y = TRACK_SIZE[1] / 2 - main_lbl.content_height / 2
        support_lbl = pyglet.text.Label(support_txt, batch=self.batch, group=foreground,
                                        color=colors[1], font_size=16)
        support_lbl.x = TRACK_SIZE[0] / 2 - support_lbl.content_width / 2
        support_lbl.y = TRACK_SIZE[1] / 2 - main_lbl.content_height - support_lbl.content_height
        exit_lbl = pyglet.text.Label(exit_txt, batch=self.batch, group=foreground,
                                     color=colors[1], font_size=16)
        exit_lbl.x = TRACK_SIZE[0] / 2 - exit_lbl.content_width / 2
        exit_lbl.y = TRACK_SIZE[1] / 2 - main_lbl.content_height - exit_lbl.content_height * 2.3


class ScoreBox(GraphicsElement):
    BG_COLOR = 50, 50, 200
    SCORE_BOX = 125, 40

    def __init__(self):
        super().__init__()
        offset = np.array(TRACK_SIZE) - self.SCORE_BOX
        box = np.append(offset, offset + self.SCORE_BOX)
        self.center_x = offset[0] + self.SCORE_BOX[0] / 2

        background = pyglet.graphics.OrderedGroup(0)
        foreground = pyglet.graphics.OrderedGroup(1)
        add_points_to(self.batch, [
            box[0], box[1], box[2], box[1], box[2], box[3], box[0], box[3], box[0], box[1]
        ], self.BG_COLOR, pyglet.gl.GL_POLYGON, background)
        self.label = pyglet.text.Label(x=TRACK_SIZE[0] - 100, y=TRACK_SIZE[1] - 25,
                                       batch=self.batch, group=foreground)

    def update_text(self, score_text):
        self.label.text = score_text
        self.label.x = self.center_x - self.label.content_width / 2
