# ===============================================================================
# rpi_weather.py
#
# Class for interfacing to Raspberry Pi with four Adafruit 8x8 LEDs attached.
#
# 2015-04-15
# Carter Nelson
# ===============================================================================
from enum import Enum
from time import sleep

from led8x8icons import LED8x8ICONS


def reset_display(display, text="BLUM"):
    display.clear_display()
    for matrix, icon in enumerate(text):
        display.scroll_raw64(LED8x8ICONS[icon], matrix)

class LEDDisplayPadding(Enum):
    NONE = 0
    PAD_EMPTY = 1
    PAD_ZEROS = 2

class LEDDisplay():
    """Class for interfacing to Raspberry Pi with four Adafruit 8x8 LEDs attached."""

    def __init__(self, size=4, brightness=0):
        import board
        import busio

        # Import the HT16K33 LED matrix module.
        from adafruit_ht16k33 import matrix

        self.matrices = []
        # Create the I2C interface.
        self.i2c = busio.I2C(board.SCL, board.SDA)
        for i in range(size):
            self.matrices.append(matrix.Matrix8x8(self.i2c, address=0x70 + i))
        for m in self.matrices:
            m.brightness = brightness

    def is_valid_matrix(self, matrix):
        """Returns True if matrix number is valid, otherwise False."""
        return matrix >=0 and matrix <= len(self.matrices)

    def clear_display(self, matrix=None):
        """Clear specified matrix. If none specified, clear all."""
        if matrix == None:
            for m in self.matrices:
                m.fill(0)
                m.show()
        else:
            if not self.is_valid_matrix(matrix):
                return
            self.matrices[matrix].fill(0)
            self.matrices[matrix].show()

    def set_pixel(self, x, y, matrix=0, value=1, write=True):
        """Set pixel at position x, y for specified matrix to the given value."""
        if not self.is_valid_matrix(matrix):
            return
        self.matrices[matrix][x, y] = value
        if write:
            self.matrices[matrix].show()

    def show(self, matrix):
        if not self.is_valid_matrix(matrix):
            return
        self.matrices[matrix].show()

    def set_bitmap(self, bitmap, matrix=0):
        """Set specified matrix to provided bitmap."""
        if not self.is_valid_matrix(matrix):
            return
        for x in range(8):
            for y in range(8):
                self.matrices[matrix][x, y] = bitmap[y][x]
        self.show(matrix)

    def set_raw64(self, value, matrix=0):
        """Set specified matrix to bitmap defined by 64 bit value."""
        if not self.is_valid_matrix(matrix):
            return
        self.matrices[matrix].fill(0)
        for y in range(8):
            row_byte = value >> (8 * y)
            for x in range(8):
                pixel_bit = row_byte >> x & 0x01
                self.matrices[matrix][x, y] = pixel_bit
        self.show(matrix)

    def scroll_raw64(self, value, matrix=0, delay=0.10):
        """Scroll out the current bitmap with the supplied bitmap. Can also
        specify a matrix (0-3) and a delay to set scroll rate.
        """
        if not self.is_valid_matrix(matrix):
            return
        auto_write = self.matrices[matrix]._auto_write
        self.matrices[matrix]._auto_write = False
        for y in range(7, -1, -1):
            row_byte = value >> (8 * y)
            for x in range(8):
                pixel_bit = row_byte >> x & 0x01
                self.matrices[matrix][x, 0] = pixel_bit
            sleep(delay)
            self.matrices[matrix]._auto_write = auto_write
            if auto_write:
                self.matrices[matrix].show()
            if y > 0:
                self.matrices[matrix].shift_up()

    def disp_number(self, number, scroll=False, padding=LEDDisplayPadding.NONE):
        """
        Display number as integer. Valid range is 0 to 9999.
        pad - pad to 4 digits so numbers are consistent in the display
        """
        if number > 9999 or number < 0:
            return
        num = str(number)
        pad_size = len(self.matrices) - len(num)
        if padding == LEDDisplayPadding.PAD_EMPTY:
            pad = " " * pad_size
        elif padding == LEDDisplayPadding.PAD_ZEROS:
            pad = "0" * pad_size
        else:
            pad = ""
        if scroll:
            render_fn = self.scroll_raw64
        else:
            render_fn = self.set_raw64
        self.clear_display()
        for i, d in enumerate(pad+num):
            render_fn(LED8x8ICONS['{0}'.format(d)], i)
