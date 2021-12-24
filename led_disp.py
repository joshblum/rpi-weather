# ===============================================================================
# rpi_weather.py
#
# Class for interfacing to Raspberry Pi with four Adafruit 8x8 LEDs attached.
#
# 2015-04-15
# Carter Nelson
# ===============================================================================
from time import sleep

from Adafruit_LED_Backpack import Matrix8x8
from led8x8icons import LED8x8ICONS


def reset_display(display, text="BLUM"):
    display.clear_display()
    for matrix, icon in enumerate(text):
        display.scroll_raw64(LED8x8ICONS[icon], matrix)


class LEDDisplay():
    """Class for interfacing to Raspberry Pi with four Adafruit 8x8 LEDs attached."""

    def __init__(self, size=4, brightness=0):
        self.matrix = []
        for i in range(size):
            self.matrix.append(Matrix8x8.Matrix8x8(address=0x70 + i, busnum=1))
        for m in self.matrix:
            m.begin()
            m.set_brightness(brightness)

    def is_valid_matrix(self, matrix):
        """Returns True if matrix number is valid, otherwise False."""
        return matrix in range(len(self.matrix))

    def clear_display(self, matrix=None):
        """Clear specified matrix. If none specified, clear all."""
        if matrix == None:
            for m in self.matrix:
                m.clear()
                m.write_display()
        else:
            if not self.is_valid_matrix(matrix):
                return
            self.matrix[matrix].clear()
            self.matrix[matrix].write_display()

    def set_pixel(self, x, y, matrix=0, value=1, write=True):
        """Set pixel at position x, y for specified matrix to the given value."""
        if not self.is_valid_matrix(matrix):
            return
        self.matrix[matrix].set_pixel(x, y, value)
        if write:
            self.write_display(matrix)

    def write_display(self, matrix):
        if not self.is_valid_matrix(matrix):
            return
        self.matrix[matrix].write_display()

    def set_bitmap(self, bitmap, matrix=0):
        """Set specified matrix to provided bitmap."""
        if not self.is_valid_matrix(matrix):
            return
        for x in range(8):
            for y in range(8):
                self.matrix[matrix].set_pixel(x, y, bitmap[y][x])
        self.write_display(matrix)

    def set_raw64(self, value, matrix=0):
        """Set specified matrix to bitmap defined by 64 bit value."""
        if not self.is_valid_matrix(matrix):
            return
        self.matrix[matrix].clear()
        for y in range(8):
            row_byte = value >> (8 * y)
            for x in range(8):
                pixel_bit = row_byte >> x & 0x01
                self.matrix[matrix].set_pixel(x, y, pixel_bit)
        self.write_display(matrix)

    def scroll_raw64(self, value, matrix=0, delay=0.12):
        """Scroll out the current bitmap with the supplied bitmap. Can also
        specify a matrix (0-3) and a delay to set scroll rate.
        """
        for step in range(7, -1, -1):
            for old_row in range(7, 0, -1):
                self.matrix[matrix].buffer[old_row *
                                           2] = self.matrix[matrix].buffer[(old_row - 1) * 2]
            new_row = (value >> (8 * step)) & 0xff
            # fix for memory buffer error
            new_row = (new_row << 7 | new_row >> 1) & 0xff
            self.matrix[matrix].buffer[0] = new_row
            self.write_display(matrix)
            sleep(delay)

    def disp_number(self, number, scroll=False):
        """Display number as integer. Valid range is 0 to 9999."""
        num = int(number)
        if num > 9999 or num < 0:
            return
        if scroll:
            render_fn = self.scroll_raw64
        else:
            render_fn = self.set_raw64
        self.clear_display()
        digits = []
        while num:
            digit = num % 10
            digits.append(digit)
            num //= 10
        for i, d in enumerate(reversed(digits)):
            render_fn(LED8x8ICONS['{0}'.format(d)], i)
