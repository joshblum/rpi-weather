#!/usr/bin/env python
# ===============================================================================
# clock.py
#
# Simple clock demo.
#
# 2014-09-12
# Carter Nelson
# ===============================================================================
import time

from led_disp import LEDDisplay, LEDDisplayPadding, reset_display
from led8x8icons import LED8x8ICONS as ICONS


def time2int(time_struct, format24=True):
    """Convert time, passed in as a time.struct_time object, to an integer with
    hours in the hundreds place and minutes in the units place. Returns 24
    hour format if format24 is True, 12 hour format (default) otherwise.
    """
    if not isinstance(time_struct, time.struct_time):
        return None
    h = time_struct.tm_hour
    m = time_struct.tm_min
    if not format24:
        h = h if h <= 12 else h - 12
    return h * 100 + m


def display_clock(display, format24=True):
    old_val = time2int(time.localtime(), format24=format24)
    padding = LEDDisplayPadding.PAD_ZEROS if format24 else LEDDisplayPadding.PAD_EMPTY
    display.disp_number(old_val, scroll=True, padding=padding)
    return True


def update_display(display, new_val, old_val):
    """Update the display, one digit at a time, where values differ."""
    if not (isinstance(new_val, int) and isinstance(old_val, int)):
        return
    if new_val == old_val:
        return
    for i in range(3, -1, -1):
        new_d = new_val % 10
        display.scroll_raw64(ICONS["{0}".format(new_d)], i)
        new_val //= 10


# -------------------------------------------------------------------------------
#  M A I N
# -------------------------------------------------------------------------------
if __name__ == "__main__":
    display = LEDDisplay()
    reset_display(display)
    time.sleep(5)
    while True:
        """Loop forever, updating every 2 seconds."""
        display_clock(display, format24=True)
        time.sleep(2)
        display_clock(display, format24=False)
        time.sleep(2)
