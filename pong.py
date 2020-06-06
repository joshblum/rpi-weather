from Adafruit_LED_Backpack import Matrix8x8
from led8x8icons import LED8x8ICONS
from led_disp import LEDDisplay
from threading import Thread
import random
import time
import copy
import curses

DEFAULT_BOARD_WIDTH = 4 * 8
DEFAULT_BOARD_HEIGHT = 8


class Point(object):

    def __init__(self, dx, dy, vx=0, vy=0, max_vx=2, max_vy=2):
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


class Piece(object):

    def __init__(self, width, height, initial_point):
        self.width = width
        self.height = height
        self.initial_point = initial_point
        self.reset()

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


class Ball(Piece):

    def __init__(self, initial_point, width=1, height=1):
        super(Ball, self).__init__(width, height, initial_point)

    def reset(self):
        self.initial_point.vy = random.randrange(-10, 10, 1) / 10.0
        super(Ball, self).reset()


class Player(Piece):

    def __init__(self, upkey, downkey, initial_point, width=1, height=3):
        super(Player, self).__init__(width, height, initial_point)
        self.upkey = upkey
        self.downkey = downkey

    def handle_key(self, key):
        if key == self.upkey:
            self.set_vy(-1)
        elif key == self.downkey:
            self.set_vy(1)

    def step(self):
        old_pos, new_pos = super(Player, self).step()
        self.set_vy(self.get_vy() * .3)
        return old_pos, new_pos


class Board(object):

    def __init__(self, player1, player2, ball,
                 width=DEFAULT_BOARD_WIDTH,
                 height=DEFAULT_BOARD_HEIGHT,
                 max_resets=5
                 ):
        self.width = width
        self.height = height
        self.running = False
        self.player1 = player1
        self.player2 = player2
        self.ball = ball
        self.array = self._init_array()
        self.num_resets = 0
        self.max_resets = max_resets

    def _init_array(self, val=0):
        array = []
        for _ in range(self.height):
            array.append([val] * self.width)
        return array

    def pieces(self):
        return [self.ball, self.player1, self.player2]

    def update_position(self, piece):
        pos, next_pos = piece.step()
        # zero out old position
        self.set_position(pos, 0)

        for x, y in next_pos:
            vx = piece.get_vx()
            vy = piece.get_vy()

            if x < 0 or x >= self.width:
                piece.set_vx(-vx)
                break
            if y < 0 or y >= self.height:
                piece.set_vy(-vy)
                break

            if self.array[y][x] == 1:
                if x == 0 or x == self.width - 1:
                    if x == 0:
                        player_vy = self.player1.get_vy()
                    else:
                        player_vy = self.player2.get_vy()
                    piece.set_vx(-vx)
                    piece.set_vy(vy + player_vy)
                    break
                if y == 0 or y == self.height - 1:
                    piece.set_vy(-vy)
                    break

        if isinstance(piece, Ball):
            for x, y in next_pos:
                y = min(y, self.height - 1)
                if x <= 0 and self.array[y][0] != 1:
                    self.reset()
                    return
                if x >= self.width - 1 and self.array[y][-1] != 1:
                    self.reset()
                    return

        if isinstance(piece, Player):
            for _, y in next_pos:
                if y <= 0 or y >= self.height - 1:
                    next_pos = pos
                    break

        self.set_position(next_pos, 1)

    def reset(self):
        for p in self.pieces():
            p.reset()
        self.array = self._init_array()
        self.num_resets += 1

    def exceeded_max_resets(self):
        return self.num_resets >= self.max_resets

    def end_game(self):
        self.array = self._init_array(val=1)

    def set_position(self, pos, value):
        for x, y in pos:
            try:
                self.array[y][x] = value
            except IndexError:
                continue


class Pong(object):

    def __init__(self, board):
        self.board = board

    def start_game(self):
        self.running = True
        while self.running:
            for piece in self.board.pieces():
                self.board.update_position(piece)
            self.render()

            if self.board.exceeded_max_resets():
                self.render_end_game()
                self.stop_game()
            time.sleep(.05)

    def stop_game(self):
        self.running = False

    def render_end_game(self):
        raise NotImplementedError()

    def render(self):
        raise NotImplementedError()

    def handle_key(self, key):
        if key == 27:  # esc or alt
            self.stop_game()

        for p in [self.board.player1, self.board.player2]:
            p.handle_key(key)


class TermPong(Pong):

    def __init__(self, board, screen):
        super(TermPong, self).__init__(board)
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

    def render_end_game(self):
        for y, row in enumerate(self.board.array):
            for x, val in enumerate(row):
                strval = "*"
                self.screen.addstr(y, x, strval)
        self.screen.refresh()


class PiPong(Pong):

    def __init__(self, board, screen):
        super(PiPong, self).__init__(board)
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

    def render_end_game(self):
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

    # starts on the left side, centered vertically at rest
    player1 = Player(ord('w'), ord('s'),
                     Point(0, DEFAULT_BOARD_HEIGHT / 2))
    # starts on the right side, centered vertically at rest
    player2 = Player(curses.KEY_UP, curses.KEY_DOWN,
                     Point(DEFAULT_BOARD_WIDTH - 1, DEFAULT_BOARD_HEIGHT / 2))

    # starts in the center heading left
    ball = Ball(Point(DEFAULT_BOARD_WIDTH / 2,
                      DEFAULT_BOARD_HEIGHT / 2, -1, 0))
    board = Board(player1, player2, ball)
    window = curses.newwin(DEFAULT_BOARD_HEIGHT + 1,
                           DEFAULT_BOARD_WIDTH + 1, 0, 0)
    try:
        # pong = TermPong(board, window)
        pong = PiPong(board, window)

        def start(): return pong.start_game()
        thread = Thread(target=start)
        thread.daemon = True

        thread.start()
        while pong.running:
            key = screen.getch()
            pong.handle_key(key)
        thread.join()
    finally:
        # shut down cleanly
        curses.nocbreak()
        screen.keypad(0)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    main()
