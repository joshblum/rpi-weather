#!/usr/bin/env python
# ===============================================================================
# weather_climacell.py
#
# Get weather forecast from ClimaCell and display as 8x8 icons
#   * https://developer.climacell.co/v3/reference#get-hourly
#   * Setup an API config according to the readme
# ===============================================================================
import requests
import traceback
import time
import random
import sys
import json
from collections import namedtuple
from datetime import datetime, tzinfo, timedelta

from led_disp import LEDDisplay, reset_display
from clock import display_clock
from led8x8icons import LED8x8ICONS


url = "https://api.tomorrow.io/v4/timelines"
icons = ["SUNNY", "RAIN", "CLOUD", "SHOWERS", "SNOW", "STORM"]
synonym_map = {
    "SUNNY": [
        "MOSTLY_CLEAR",
        "CLEAR",
    ],
    "RAIN": [
        "RAIN",
        "RAIN_LIGHT",
    ],
    "CLOUD": [
        "CLOUDY",
        "MOSTLY_CLOUDY",
        "PARTLY_CLOUDY",
    ],
    "SHOWERS": [
        "DRIZZLE",
        "FOG_LIGHT",
        "FOG",
    ],
    "SNOW": [
        "FREEZING_RAIN_HEAVY",
        "FREEZING_RAIN",
        "FREEZING_RAIN_LIGHT",
        "FREEZING_DRIZZLE",
        "ICE_PELLETS_HEAVY",
        "ICE_PELLETS",
        "ICE_PELLETS_LIGHT",
        "SNOW_HEAVY",
        "SNOW",
        "SNOW_LIGHT",
        "FLURRIES",
    ],
    "STORM": [
        "RAIN_HEAVY",
        "TSTORM",
    ],
}

# https://docs.tomorrow.io/reference/data-layers-overview
moon_phase_map = {
    0: "NEW",
    1: "WAXING_CRESCENT",
    2: "FIRST_QUARTER",
    3: "WAXING_GIBBOUS",
    4: "FULL",
    5: "WANING_GIBBOUS",
    6: "LAST_QUARTER",
    7: "WANING_CRESCENT",
}

weather_code_map = {
    0: "UNKNOWN",
    1000: "SUNNY",
    1001: "CLOUD",
    1100: "MOSTLY_CLEAR",
    1101: "PARTLY_CLOUDY",
    1102: "MOSTLY_CLOUDY",
    2000: "FOG",
    2100: "FOG_LIGHT",
    3000: "SUNNY",  # light wind
    3001: "SUNNY",  # wind
    3002: "SUNNY",  # strong wind
    4000: "DRIZZLE",
    4001: "RAIN",
    4200: "RAIN_LIGHT",
    4201: "RAIN_HEAVY",
    5000: "SNOW",
    5001: "FLURRIES",
    5100: "SNOW_LIGHT",
    5101: "SNOW_HEAVY",
    6000: "FREEZING_DRIZZLE",
    6001: "FREEZING_RAIN",
    6200: "FREEZING_RAIN_LIGHT",
    6201: "FREEZEING_RAIN_HEAVY",
    7000: "ICE_PELLETS",
    7101: "ICE_PELLETS_HEAVY",
    7102: "ICE_PELLETS_LIGHT",
    8000: "TSTORM",
}

Prediction = namedtuple("Prediction", ["temp", "condition_icon", "moon_icon"])
Forecast = namedtuple("Forecast", ["predictions"])


def read_config(filename):
    with open(filename) as f:
        data = json.load(f)
        return data["apikey"], data["lat"], data["lon"]


class simple_utc(tzinfo):
    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def make_climacell_request(apikey, lat, lon):
    r = requests.request(
        "GET",
        url,
        params={
            "location": "{},{}".format(lat, lon),
            "apikey": apikey,
            "units": "imperial",
            "timesteps": "1h",
            "startTime": "now",
            "endTime": "nowPlus1d",
            # include but later ignore 1d to allow moonPhase -_-
            "timesteps": ["1h", "1d"],
            "fields": ["temperatureApparent", "weatherCode", "moonPhase"],
        },
    )
    return r.json()


def normalize_condition_icon(condition):
    condition = condition.upper()
    for icon, synonyms in synonym_map.items():
        if icon in condition:
            return icon
        for synonym in synonyms:
            if synonym in condition:
                return icon
    print("Missing icon for daily forecast", condition)
    return "UNKNOWN"


def get_condition_icon(resp_prediction):
    return normalize_condition_icon(
        weather_code_map.get(resp_prediction.get("weatherCode", 0), "UNKNOWN")
    )


def get_moon_icon(resp_prediction):
    return moon_phase_map.get(resp_prediction.get("moonPhase", 0), "UNKNOWN").upper()


def get_temp(resp_prediction):
    return int(resp_prediction.get("temperatureApparent", 0))


def make_prediction(resp_prediction):
    resp_prediction = resp_prediction.get("values")
    return Prediction(
        condition_icon=get_condition_icon(resp_prediction),
        moon_icon=get_moon_icon(resp_prediction),
        temp=get_temp(resp_prediction),
    )


def get_climacell_forecast(apikey, lat, lon):
    response = make_climacell_request(apikey, lat, lon)
    resp = response.get("data", {}).get("timelines", [])
    if not isinstance(resp, list) or len(resp) == 0:
        print("unexpected response {}".format(response))
        return None
    for d in resp:
        if d.get("timestep", "") == "1h":
            intervals = d.get("intervals", [])
            predictions = list(map(make_prediction, intervals))
            # restrict this to just the next 8 hours
            return Forecast(predictions=predictions[:8])
    print("unexpected response {}".format(response))
    return None


def print_forecast(forecast=None):
    """Print forecast to screen."""
    print("-" * 20)
    print(time.strftime("%Y/%m/%d %H:%M:%S"))
    print("-" * 20)
    if forecast is None:
        print("null forecast")
    else:
        for p in forecast.predictions:
            print(p)


def display_hi_low(display, forecast=None, show_hi=True):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast is None or not len(forecast.predictions):
        return False

    prediction = forecast.predictions[0]
    display.scroll_raw64(LED8x8ICONS[prediction[0].condition_icon], 0)

    icon = "UP_ARROW" if show_hi else "DOWN_ARROW"
    display.scroll_raw64(LED8x8ICONS[icon], 1)

    fn = max if show_hi else min
    temp = str(fn(forecast.predictions, key=lambda x: x.temp).temp).zfill(2)
    offset = 1 if len(temp) == 3 else 2
    for i, d in enumerate(temp):
        display.scroll_raw64(LED8x8ICONS["{0}".format(d)], i + offset)
    return True


def display_current_forecast(display, forecast=None):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast is None or not len(forecast.predictions):
        return False
    prediction = forecast.predictions[0]

    display.scroll_raw64(LED8x8ICONS[prediction.moon_icon], 0)
    display.scroll_raw64(LED8x8ICONS[prediction.condition_icon], 1)

    temp = str(prediction.temp).zfill(2)
    offset = 1 if len(temp) == 3 else 2
    for i, d in enumerate(temp):
        display.scroll_raw64(LED8x8ICONS["{0}".format(d)], i + offset)
    return True


def display_8_hr_forecast(display, forecast=None):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast is None:
        return False

    max_i = 4
    offset = len(forecast.predictions) // max_i
    for i, pidx in enumerate(range(0, len(forecast.predictions), offset)):
        if i >= max_i:
            break
        condition_icon = forecast.predictions[pidx].condition_icon
        display.scroll_raw64(LED8x8ICONS[condition_icon], i)
    return True


class ForecastState:
    def __init__(self, timeout):
        self.forecast = None
        self.last_fetched = datetime.min
        self.last_updated = datetime.min
        self.timeout_sec = timeout
        self.backoff_sec = 0

    def maybe_refresh(self):
        # if we don't haven't forecast or haven't recently updated we need to attempt
        last_update = datetime.now() - self.last_updated
        need_update = self.forecast is None or (
            last_update.total_seconds() >= self.timeout_sec
        )
        if not need_update:
            return
        elapsed = datetime.now() - self.last_fetched
        if elapsed.total_seconds() < self.backoff_sec:
            return

        print("Fetching new forecast")
        f = None
        try:
            f = get_climacell_forecast(apikey, lat, lon)
        except:
            traceback.print_exc()
        self.last_fetched = datetime.now()

        # on failure don't overwrite a forecast if we have one, just set the backoff.
        if f is None:
            if self.backoff_sec == 0:
                self.backoff_sec = 2
            else:
                self.backoff_sec *= 2
            self.backoff_sec = min(self.backoff_sec, self.timeout_sec)
            print("unable to fetch forecast, backoff_sec: {}".format(self.backoff_sec))
            return

        self.backoff_sec = 0
        self.forecast = f
        self.last_updated = datetime.now()
        print_forecast(self.forecast)
        print("next update in {} seconds".format(self.timeout_sec))

    def get_forecast(self):
        return self.forecast


# -------------------------------------------------------------------------------
#  M A I N
# -------------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "climacell_cfg.json"

    programs = {
        "clock": lambda d, f: display_clock(d),  # 24h default
        "clock_12": lambda d, f: display_clock(d, format24=False),
        "clock_24": lambda d, f: display_clock(d, format24=True),
        "hi_forecast": lambda d, f: display_hi_low(d, f, show_hi=False),
        "low_forecast": display_hi_low,
        "current_forecast": display_current_forecast,  # moon phase || current condition || temp
        "8_hr_forecast": display_8_hr_forecast,
    }
    program = []
    for arg in sys.argv[2:]:
        if arg in programs:
            program.append(programs[arg])
        else:
            raise Exception("expected one of {}, found {}".format(programs.keys(), arg))

    if not len(program):
        program = [display_current_forecast]

    apikey, lat, lon = read_config(filename)
    display = None
    while True:
        try:
            print("creating display")
            # power through any initial I/O errors
            display = LEDDisplay()
            reset_display(display)
            break
        except:
            traceback.print_exc()
            time.sleep(1)

    timeout = 60 * 60  # 1 hour
    forecast = ForecastState(timeout)
    while True:
        for step in program:
            try:
                forecast.maybe_refresh()
                if step(display, forecast.get_forecast()):
                    time.sleep(2)
                    display.clear_display()
            except:
                traceback.print_exc()
                time.sleep(2)
