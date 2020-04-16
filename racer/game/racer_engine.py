import math

import numpy as np
from shapely.geometry import Polygon

from .tracks import OUTER_TRACK, OUTER_TRACK_OFFSET, \
    INNER_TRACK, INNER_TRACK_OFFSET, \
    INIT_CAR_POSITION, INIT_CAR_ROTATION

CAR_BOUNDS = (-15, -11, 33, 11)
CAR_BOUND_POINTS = (CAR_BOUNDS[0], CAR_BOUNDS[1], CAR_BOUNDS[2], CAR_BOUNDS[1],
                    CAR_BOUNDS[2], CAR_BOUNDS[3], CAR_BOUNDS[0], CAR_BOUNDS[3]
                    )
CAR_COLL_BOX = np.reshape(CAR_BOUND_POINTS, (-1, 2)) * 0.95
MAX_CAR_SPEED = 300
MAX_CAR_ROTATION = 200
CAR_FRICTION = 0.98
MIN_SPEED = 10


class PlayerOperation:
    FWD_IX = 0
    REV_IX = 1
    LEFT_IX = 2
    RIGHT_IX = 3

    def __init__(self):
        self._data = [False] * 4

    def get_move_factor(self):
        if self._data[self.FWD_IX]:
            return 1
        if self._data[self.REV_IX]:
            return -1
        return 0

    def get_turn_factor(self):
        if self._data[self.LEFT_IX]:
            return -1
        if self._data[self.RIGHT_IX]:
            return 1
        return 0

    def accelerate(self):
        self._data[self.FWD_IX] = True
        self._data[self.REV_IX] = False

    def reverse(self):
        self._data[self.FWD_IX] = False
        self._data[self.REV_IX] = True

    def stop_direction(self):
        self._data[self.FWD_IX] = False
        self._data[self.REV_IX] = False

    def turn_left(self):
        self._data[self.LEFT_IX] = True
        self._data[self.RIGHT_IX] = False

    def turn_right(self):
        self._data[self.LEFT_IX] = False
        self._data[self.RIGHT_IX] = True

    def stop_left(self):
        self._data[self.LEFT_IX] = False

    def stop_right(self):
        self._data[self.RIGHT_IX] = False

    def stop_all(self):
        self._data[self.FWD_IX] = False
        self._data[self.REV_IX] = False
        self._data[self.LEFT_IX] = False
        self._data[self.RIGHT_IX] = False


class RacerEngine:
    def __init__(self):
        self.player_state = PlayerState()
        self.track = Track()
        self.__game_over = False

    @property
    def game_over(self):
        return self.__game_over

    @game_over.setter
    def game_over(self, game_over):
        self.player_state.is_alive = not game_over
        self.__game_over = game_over

    def update(self, dt, operations):
        self.player_state.update(dt, operations)
        if not self.track.contains(self.player_state.boundaries):
            self.game_over = True


class PlayerState:
    def __init__(self):
        [self.x, self.y], self.rotation = INIT_CAR_POSITION, INIT_CAR_ROTATION
        self.speed = 0
        self.boundaries = Polygon(np.reshape(CAR_BOUND_POINTS, (-1, 2)))
        self.is_alive = True

    @property
    def relevant_speed(self):
        if self.__ignore_speed():
            return 0
        return self.speed

    def __ignore_speed(self):
        return abs(self.speed) < MIN_SPEED

    def update(self, dt, operations: PlayerOperation):
        self.speed *= CAR_FRICTION
        move_fact = operations.get_move_factor()
        if move_fact:
            new_speed = self.speed + MAX_CAR_SPEED * dt * move_fact
            self.speed = min(MAX_CAR_SPEED, max(-MAX_CAR_SPEED, new_speed))
        elif self.__ignore_speed():
            self.speed = 0

        if not self.__ignore_speed():
            turn_fact = operations.get_turn_factor() * math.copysign(1, self.speed)
            allowed_rot = MAX_CAR_ROTATION * ((abs(self.speed) / MAX_CAR_SPEED) ** 0.5)
            self.rotation += allowed_rot * dt * turn_fact

        rot = math.radians(self.rotation)
        cosine, sine = math.cos(rot), math.sin(rot)
        self.x += cosine * self.speed * dt
        self.y -= sine * self.speed * dt
        self.__update_boundaries__(cosine, sine)

    def __update_boundaries__(self, cosine, sine):
        j = np.array([[cosine, sine], [-sine, cosine]])
        new_boundaries = []
        for ix in range(len(CAR_COLL_BOX)):
            m = np.dot(j, CAR_COLL_BOX[ix])
            moved = np.array((self.x, self.y)) + m.T
            new_boundaries.append(moved)
        self.boundaries = Polygon(new_boundaries)

    def flattened_boundaries(self):
        return np.array(self.boundaries.coords[:-1]).flatten()


class Track:
    def __init__(self):
        self.__outside = TrackLines(OUTER_TRACK, OUTER_TRACK_OFFSET)
        self.__inside = TrackLines(INNER_TRACK, INNER_TRACK_OFFSET)

    def contains(self, geometry):
        return self.__outside.area.contains(geometry) and \
               not self.__inside.area.intersects(geometry)


class TrackLines:
    def __init__(self, track, offset):
        points = np.reshape(track, (-1, 2))
        self.area = Polygon(points)
