from os import path

import numpy as np
import pyglet
from pyglet.graphics.vertexdomain import VertexList
from shapely.geometry import Point, LinearRing

from .racer_engine import PlayerState, CAR_BOUND_POINTS, CAR_BOUNDS
from .tracers import get_trace_points
from .tracks import OUTER_TRACK, INNER_TRACK, TRACK_SIZE

resource_dir = path.join(path.abspath(path.dirname(__file__)), 'resources')
pyglet.resource.path = [resource_dir]
pyglet.resource.reindex()
car_frame_img = pyglet.resource.image('car-frame.png')
car_frame_img.anchor_x = car_frame_img.width // 3
car_frame_img.anchor_y = car_frame_img.height // 2
pointer_img = pyglet.resource.image('pointer.png')
pointer_img.anchor_x = pointer_img.width // 2
pointer_img.anchor_y = pointer_img.height // 2


def random_color():
    return tuple(np.random.randint(0, 255, size=3))


def convert_data(points, color=None, color_mode='c3B'):
    pts_count = len(points) // 2
    vertices = ('v2i', points)
    color_data = (color_mode, color * pts_count) if color else None
    return pts_count, vertices, color_data


def create_vertex_list(points, color, color_mode='c3B'):
    pts, vertices, color_data = convert_data(points, color, color_mode)
    return pyglet.graphics.vertex_list(pts, vertices, color_data)


class GraphicsElement:
    def __init__(self):
        self.batch = pyglet.graphics.Batch()

    def draw(self):
        self.batch.draw()

    def add_points(self, points, color, mode=pyglet.gl.GL_LINE_STRIP, group=None) -> VertexList:
        pts_count, vertices, color_data = convert_data(points, color)
        return self.batch.add(pts_count, mode, group, vertices, color_data)


class CarGraphics(GraphicsElement):
    TRACE_COLOR = 100, 100, 255
    DEAD_COLOR = 255, 70, 70
    DEAD_BG_COLOR = 70, 70, 70, 150

    def __init__(self, show_traces=True):
        super().__init__()
        self.show_traces = show_traces
        self.car_frame = pyglet.sprite.Sprite(img=car_frame_img, batch=self.batch)
        self.car_frame.scale = 0.5

        color_data = 'c3B', random_color() + random_color() + random_color() + random_color()
        pts, vertices, _ = convert_data(CAR_BOUND_POINTS)
        self.car_color = pyglet.graphics.vertex_list(pts, vertices, color_data)

        line_1 = [CAR_BOUNDS[0] + 1, CAR_BOUNDS[1] + 2, CAR_BOUNDS[2] - 1, CAR_BOUNDS[3] - 1]
        line_2 = [CAR_BOUNDS[0] + 1, CAR_BOUNDS[3] - 1, CAR_BOUNDS[2] - 1, CAR_BOUNDS[1] + 2]
        self.dead_x = [create_vertex_list(CAR_BOUND_POINTS, self.DEAD_BG_COLOR, 'c4B'),
                       create_vertex_list(line_1, self.DEAD_COLOR),
                       create_vertex_list(line_2, self.DEAD_COLOR)]
        self.show_dead_x = False

    def draw(self):
        if self.show_traces:
            self.__draw_traces()

        self.__draw_at_car_position(lambda: self.car_color.draw(pyglet.gl.GL_POLYGON))
        self.batch.draw()
        if self.show_dead_x:
            self.__draw_at_car_position(self.__draw_dead_x)

    def __draw_traces(self):
        pyglet.gl.glLineWidth(1)
        for pos in get_trace_points(self.car_frame.position, self.car_frame.rotation):
            pyglet.graphics.draw(2, pyglet.gl.GL_LINE_STRIP,
                                 ('v2f', self.car_frame.position + pos),
                                 ('c3B', self.TRACE_COLOR * 2)
                                 )

    def __draw_dead_x(self):
        pyglet.gl.glLineWidth(5)
        [box, line_1, line_2] = self.dead_x
        line_1.draw(pyglet.gl.GL_LINE_STRIP)
        line_2.draw(pyglet.gl.GL_LINE_STRIP)
        box.draw(pyglet.gl.GL_POLYGON)

    def __draw_at_car_position(self, draw_callback):
        pyglet.gl.glPushMatrix()
        pyglet.gl.glTranslatef(self.car_frame.x, self.car_frame.y, 0)
        pyglet.gl.glRotatef(-self.car_frame.rotation, 0, 0, 1.0)
        draw_callback()
        pyglet.gl.glPopMatrix()

    def update(self, player: PlayerState):
        self.car_frame.update(x=player.x, y=player.y, rotation=player.rotation)
        self.show_dead_x = not player.is_alive


class TrackGraphics(GraphicsElement):
    TRACK_COLOR = 160, 10, 60

    def __init__(self):
        super().__init__()
        self.add_points(OUTER_TRACK, self.TRACK_COLOR)
        self.add_points(INNER_TRACK, self.TRACK_COLOR)

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
        bg_box = [box[0], box[1], box[2], box[1], box[2], box[3], box[0], box[3], box[0], box[1]]
        self.add_points(bg_box, self.BG_COLOR, pyglet.gl.GL_POLYGON, background)
        self.label = pyglet.text.Label(x=TRACK_SIZE[0] - 100, y=TRACK_SIZE[1] - 25,
                                       batch=self.batch, group=foreground)

    def update_text(self, score_text):
        self.label.text = score_text
        self.label.x = self.center_x - self.label.content_width / 2


class FPSLabel(GraphicsElement):
    TEXT_COLOR = (0, 0, 0, 200)
    COLLECT_SIZE = 5

    def __init__(self):
        super().__init__()
        self.label = pyglet.text.Label('0', x=5, y=TRACK_SIZE[1] - 17,
                                       font_size=12, color=self.TEXT_COLOR,
                                       batch=self.batch)
        self.dts = []

    def update(self, dt):
        self.dts.append(dt)
        if len(self.dts) >= self.COLLECT_SIZE:
            fps = 1 / np.mean(self.dts)
            self.label.text = '{:.0f}'.format(fps)
            self.dts.clear()


class Indicator(GraphicsElement):
    OUTER_LINE = LinearRing(np.reshape(OUTER_TRACK, (-1, 2)))
    INNER_LINE = LinearRing(np.reshape(INNER_TRACK, (-1, 2)))
    out_len, in_len = len(OUTER_TRACK), len(INNER_TRACK)
    OUTER_ENDS = [(OUTER_TRACK[0], OUTER_TRACK[1]), (OUTER_TRACK[out_len - 2], OUTER_TRACK[out_len - 1])]
    INNER_ENDS = [(INNER_TRACK[0], INNER_TRACK[1]), (INNER_TRACK[in_len - 2], INNER_TRACK[in_len - 1])]

    def __init__(self):
        super().__init__()
        self.inner_point = pyglet.sprite.Sprite(img=pointer_img, batch=self.batch)
        self.outer_point = pyglet.sprite.Sprite(img=pointer_img, batch=self.batch)
        self.inner_label = pyglet.text.Label('0', font_size=14, batch=self.batch)
        self.outer_label = pyglet.text.Label('0', font_size=14, batch=self.batch)

        self.outer_offset = 3522
        self.inner_offset = 2890

    def update(self, state: PlayerState):
        pt = Point(state.x, state.y)
        # outd = np.round(self.OUTER_LINE.project(pt))
        # outd = outd - self.outer_offset
        # ind = np.round(self.INNER_LINE.project(pt))
        # print('out: {:4f}'.format(outd - self.outer_offset))
        self.__update_pointer(self.inner_point, self.inner_label, 2890, self.INNER_LINE, pt)
        self.__update_pointer(self.outer_point, self.outer_label, 3522, self.OUTER_LINE, pt)

    @staticmethod
    def __update_pointer(pointer, label, offset, line, point):
        d = line.project(point)
        label.text = '{:.0f}'.format(d - offset)
        p = line.interpolate(d)
        (px, py) = list(p.coords)[0]
        pointer.update(x=px, y=py)
        label.x = px + 8
        label.y = py + 8