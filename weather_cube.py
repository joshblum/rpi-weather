import sys
import time
from led_disp import LEDDisplay
from weather_climacell import (
    reset_display,
    get_climacell_forecast,
    print_forecast,
    read_config,
)
from datetime import datetime
from led8x8icons import LED8x8ICONS

# -------------------------------------------------------------------------------
#  M A I N
# -------------------------------------------------------------------------------


def display_cube(display, icon):
    display.scroll_raw64(LED8x8ICONS[icon], 0)


def round_temp_to_icon(temp):
    d = 0
    if temp < 100:
        d = temp / 10
    elif temp >= 100:
        d = 9  # approximate > 100 to 1 digit
    icon = "{0}".format(d)
    return icon


if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "climacell_cfg.json"
    apikey, lat, lon = read_config(filename)
    display = LEDDisplay(size=1)
    reset_display(display)
    forecast = None
    last_fetched = datetime.now()
    timeout = 60 * 60  # 1 hour
    i = 0
    while True:
        try:
            elapsed = datetime.now() - last_fetched
            if elapsed.total_seconds() >= timeout or forecast is None:
                print("Fetching new forecast")
                last_fetched = datetime.now()
                forecast = get_climacell_forecast(apikey, lat, lon)
                print_forecast(forecast)

            if forecast is None or len(forecast.predictions) == 0:
                time.sleep(2)
                continue

            prediction = forecast.predictions[0]

            if i == 0:
                display_cube(display, prediction.condition_icon)
            elif i == 1:
                display_cube(display, prediction.moon_icon)
            elif i == 2:
                display_cube(display, round_temp_to_icon(prediction.temp))

            time.sleep(2)

            i += 1
            i %= 3
        except Exception as e:
            print("unhandled exception", e)
