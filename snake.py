from led8x8icons import LED8x8ICONS
from led_disp import LEDDisplay
from threading import Thread
import time
import copy
import curses
import random

DEFAULT_BOARD_WIDTH = 4 * 8
DEFAULT_BOARD_HEIGHT = 8


class Point(object):

    def __init__(self, dx, dy, vx, vy, max_vx=2, max_vy=2):
        self.dx = dx
        self.dy = dy
        self.vx = vx
        self.vy = vy
        self.max_vx = max_vx
        self.max_vy = max_vy

    def step(self):
        self.dx += self.vx
        self.dy += self.vy

    def _clip_v(self, new_v, max_v):
        v = min(abs(new_v), max_v)
        if new_v < 0:
            v *= -1
        return v

    def set_vx(self, new_vx):
        self.vx = self._clip_v(new_vx, self.max_vx)

    def set_vy(self, new_vy):
        self.vy = self._clip_v(new_vy, self.max_vy)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "<Point at dx={}, dy={}, vx={}, vy={}>".format(
                self.dx, self.dy,
                self.vx, self.vy)


class Piece(object):

    def __init__(self, width, height, initial_point):
        self.width = width
        self.height = height
        self.initial_point = initial_point
        self.point = copy.copy(self.initial_point)

    def reset(self):
        self.point = copy.copy(self.initial_point)

    def get_position(self):
        old_x = self.point.dx
        old_y = self.point.dy
        coords = []
        for i in range(self.width):
            for j in range(self.height):
                pair = (old_x + i, old_y + j)
                pair = list(map(lambda x: abs(int(x)), pair))
                coords.append(pair)
        return coords

    def step(self):
        old_position = self.get_position()
        self.point.step()
        new_position = self.get_position()
        return old_position, new_position

    def set_vx(self, vx):
        self.point.set_vx(vx)

    def set_vy(self, vy):
        self.point.set_vy(vy)

    def get_vx(self):
        return self.point.vx

    def get_vy(self):
        return self.point.vy


class Nutrient(Piece):

    def __init__(self, dx, dy):
        return super(Nutrient, self).__init__(1, 1,
                                              Point(dx, dy, 0, 0))

    @staticmethod
    def new_random(width, height):
        dx = random.randint(0, width - 1)
        dy = random.randint(0, height - 1)
        return Nutrient(dx, dy)

    def __str__(self):
        return "<Nutrient at {}>".format(self.point)


class Snake(Piece):

    def __init__(self, initial_point):
        super(Snake, self).__init__(1, 1, initial_point)
        self.arr = [self.point]
        self.upkey = curses.KEY_UP
        self.downkey = curses.KEY_DOWN
        self.leftkey = curses.KEY_LEFT
        self.rightkey = curses.KEY_RIGHT

    def append_head(self, x, y):
        self.arr.insert(1, Point(x, y, 0, 0))

    def get_position(self):
        coords = []
        for point in self.arr:
            coords.append(
                list(map(
                    lambda x: int(x), (point.dx, point.dy))
                ))
        return coords

    def reset(self):
        super(Snake, self).reset()
        self.arr = [self.point]

    def step(self):
        old_position = self.get_position()
        head = self.arr[0]
        tail = self.arr.pop()
        tail.dx = head.dx
        tail.dy = head.dy
        head.step()
        self.arr.insert(1, tail)
        new_position = self.get_position()
        return old_position, new_position

    def handle_key(self, key):
        # exactly one of vx or vy is non-zero
        vx = self.get_vx()
        vy = self.get_vy()
        if abs(vx) > 0:
            if key == self.upkey:
                self.set_vx(0)
                self.set_vy(-1)
            elif key == self.downkey:
                self.set_vx(0)
                self.set_vy(1)
        elif abs(vy) > 0:
            if key == self.leftkey:
                self.set_vx(-1)
                self.set_vy(0)
            elif key == self.rightkey:
                self.set_vx(1)
                self.set_vy(0)

    def __len__(self):
        return len(self.arr)

    def __str__(self):
        return "<Snake {}>".format(self.arr)


class Board(object):

    def __init__(self, snake, nutrient=None,
                 width=DEFAULT_BOARD_WIDTH,
                 height=DEFAULT_BOARD_HEIGHT,
                 max_resets=5,
                 ):
        self.snake = snake
        if nutrient is None:
            nutrient = Nutrient.new_random(width, height)
        self.nutrient = nutrient
        self.width = width
        self.height = height

        self.array = self._init_array()
        self.num_resets = 0
        self.max_resets = max_resets

    def _init_array(self, val=0):
        array = []
        for _ in range(self.height):
            array.append([val] * self.width)
        return array

    def update_position(self, piece):
        pos, next_pos = piece.step()
        # zero out old position
        self.set_position(pos, 0)

        for x, y in next_pos:
            vx = piece.get_vx()
            vy = piece.get_vy()

            is_collision = False
            is_nutrient = False
            if x < 0 or x >= self.width:
                is_collision = True
                break
            if y < 0 or y >= self.height:
                is_collision = True
                break

            if self.array[y][x] == 1:
                is_collision = True
                if x > 0 and x < self.width:
                    is_nutrient = True
                    break
                if y > 0 and y < self.height:
                    is_nutrient = True
                    break
                break

        if is_nutrient:
            self.snake.append_head(x, y)
            # TODO make sure no collision with snake?
            self.nutrient = Nutrient.new_random(
                    self.width, self.height)
        elif is_collision:
            self.reset()
            return

        self.set_position(next_pos, 1)

    def reset(self):
        self.snake.reset()
        self.nutrient = Nutrient.new_random(self.width, self.height)
        self.array = self._init_array()
        self.num_resets += 1

    def exceeded_max_resets(self):
        return self.num_resets >= self.max_resets

    def end(self):
        self.array = self._init_array(val=1)

    def set_position(self, pos, value):
        for x, y in pos:
            try:
                self.array[y][x] = value
            except IndexError:
                continue


class Game(object):

    def __init__(self, board):
        self.board = board
        self.step_speed = 1
        self.running = False

    def start(self):
        self.running = True
        while self.running:
            self.board.update_position(self.board.snake)
            pos = self.board.nutrient.get_position()
            self.board.set_position(pos, 1)
            self.step_speed = .5 / len(self.board.snake)
            self.render()

            if self.board.exceeded_max_resets():
                self.render_end()
                self.stop()
            time.sleep(self.step_speed)

    def stop(self):
        self.running = False

    def render_end(self):
        raise NotImplementedError()

    def render(self):
        raise NotImplementedError()

    def handle_key(self, key):
        if key == 27:  # esc or alt
            self.stop()
            return

        self.board.snake.handle_key(key)


class TermDisp(Game):

    def __init__(self, board, screen):
        super(TermDisp, self).__init__(board)
        self.screen = screen

    def render(self):
        for y, row in enumerate(self.board.array):
            for x, val in enumerate(row):
                strval = " "
                if val == 1:
                    strval = "*"
                try:
                    self.screen.addstr(y, x, strval)
                except Exception as e:
                    print(y, x, val, e)
        self.screen.refresh()

    def render_end(self):
        for y, row in enumerate(self.board.array):
            for x, val in enumerate(row):
                strval = "*"
                self.screen.addstr(y, x, strval)
        self.screen.refresh()


class PiDisp(Game):

    def __init__(self, board, screen):
        super(PiDisp, self).__init__(board)
        self.display = LEDDisplay()
        self.display.clear_display()

    def render(self):
        for y, row in enumerate(self.board.array):
            for x, value in enumerate(row):
                matrix = x / 8
                self.display.set_pixel(x % 8, y % 8,
                                       matrix=matrix, value=value, write=False)
        for matrix in range(len(self.display.matrix)):
            self.display.write_display(matrix)

    def render_end(self):
        for matrix in range(len(self.display.matrix)):
            self.display.set_raw64(LED8x8ICONS['UNKNOWN'], matrix)


def main():
    # get the curses screen window
    screen = curses.initscr()
    # turn off input echoing
    curses.noecho()
    # respond to keys immediately (don't wait for enter)
    curses.cbreak()
    # map arrow keys to special values
    screen.keypad(True)

    try:
        snake = Snake(Point(0, DEFAULT_BOARD_HEIGHT / 2, 1, 0))

        board = Board(snake)
        window = curses.newwin(DEFAULT_BOARD_HEIGHT + 1,
                               DEFAULT_BOARD_WIDTH + 1, 0, 0)
        # game = TermDisp(board, window)
        game = PiDisp(board, window)

        def start(): return game.start()
        thread = Thread(target=start)
        thread.daemon = True

        thread.start()
        while game.running:
            key = screen.getch()
            game.handle_key(key)
        thread.join()
    finally:
        # shut down cleanly
        print("snake:", snake.arr, "nutrient:", board.nutrient)
        curses.nocbreak()
        screen.keypad(0)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    main()
