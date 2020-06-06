#!/usr/bin/env python
# ===============================================================================
# weather_climacell.py
#
# Get weather forecast from ClimaCell and display as 8x8 icons
#   * https://developer.climacell.co/v3/reference#get-hourly
#   * Setup an API config according to the readme
# ===============================================================================
import requests
import datetime
import time
import random
import sys
import json
from collections import namedtuple
from datetime import datetime, tzinfo, timedelta

from led_disp import LEDDisplay, reset_display
from clock import display_clock
from led8x8icons import LED8x8ICONS


url = "https://api.climacell.co/v3/weather/forecast/hourly"
icons = ['SUNNY', 'RAIN', 'CLOUD', 'SHOWERS', 'SNOW', 'STORM']
synonym_map = {
    'SUNNY': [
        'MOSTLY_CLEAR',
        'CLEAR',
    ],
    'RAIN': [
        'RAIN',
        'RAIN_LIGHT',
    ],
    'CLOUD': [
        'CLOUDY',
        'MOSTLY_CLOUDY',
        'PARTLY_CLOUDY',
    ],
    'SHOWERS': [
        'DRIZZLE',
        'FOG_LIGHT',
        'FOG',
    ],
    'SNOW': [
        'FREEZING_RAIN_HEAVY',
        'FREEZING_RAIN',
        'FREEZING_RAIN_LIGHT',
        'FREEZING_DRIZZLE',
        'ICE_PELLETS_HEAVY',
        'ICE_PELLETS',
        'ICE_PELLETS_LIGHT',
        'SNOW_HEAVY',
        'SNOW',
        'SNOW_LIGHT',
        'FLURRIES',
    ],
    'STORM': [
        'RAIN_HEAVY',
        'TSTORM',
    ],
}

Prediction = namedtuple('Prediction', ['temp', 'condition_icon', 'moon_icon'])
Forecast = namedtuple('Forecast', ['predictions'])


def read_config(filename):
    with open(filename) as f:
        data = json.load(f)
        return data['apikey'], data['lat'], data['lon']

class simple_utc(tzinfo):
    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def make_climacell_request(apikey, lat, lon):
    now = datetime.utcnow().replace(tzinfo=simple_utc())
    return requests.request("GET", url, params={
        'lat': lat,
        'lon': lon,
        'apikey': apikey,
        'unit_system': 'us',
        'start_time': now.isoformat(),
        'end_time': (now + timedelta(hours=8)).isoformat(),
        'fields': ['feels_like', 'weather_code', 'moon_phase'],
    }).json()


def normalize_condition_icon(condition):
    condition = condition.upper()
    for icon, synonyms in synonym_map.items():
        if icon in condition:
            return icon
        for synonym in synonyms:
            if synonym in condition:
                return icon
    print('Missing icon for daily forecast', condition)
    return 'UNKNOWN'


def get_condition_icon(resp_prediction):
    return normalize_condition_icon(
        resp_prediction.get("weather_code", {}).get("value", "UNKNOWN"))


def get_moon_icon(resp_prediction):
    return resp_prediction.get("moon_phase", {}).get("value", "UNKNOWN").upper()


def get_temp(resp_prediction):
    return int(resp_prediction.get("feels_like", {}).get("value", 0))

def make_prediction(resp_prediction):
    return Prediction(condition_icon=get_condition_icon(resp_prediction),
            moon_icon=get_moon_icon(resp_prediction),
            temp=get_temp(resp_prediction))

def get_climacell_forecast(apikey, lat, lon):
    resp = make_climacell_request(apikey, lat, lon)
    resp = resp or [{}]
    if not isinstance(resp, list) or len(resp) == 0:
        print("unexpected response {}".format(resp))
        return None
    predictions = map(make_prediction, resp)
    return Forecast(predictions=predictions)


def print_forecast(forecast=None):
    """Print forecast to screen."""
    print('-' * 20)
    print(time.strftime('%Y/%m/%d %H:%M:%S'))
    print('-' * 20)
    if forecast is None:
        print('null forecast')
    else:
        for p in forecast.predictions:
            print(p)


def display_current_forecast(display, forecast=None):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast == None or len(forecast.predictions) < 1 :
        return
    prediction = forecast.predictions[0]

    i = 0
    display.scroll_raw64(LED8x8ICONS[prediction.moon_icon], i)

    i = 1
    display.scroll_raw64(LED8x8ICONS[prediction.condition_icon], i)

    temp = prediction.temp
    digits = []
    while temp > 0:
        new_d = temp % 10
        digits.append(new_d)
        temp /= 10
    offset = 2
    for i, d in enumerate(reversed(digits)):
        display.scroll_raw64(LED8x8ICONS['{0}'.format(d)], i + offset)


def display_8_hr_forecast(display, forecast=None):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast is None:
        return

    max_i = 4
    offset = len(forecast.predictions) // max_i
    for i, pidx in enumerate(range(0, len(forecast.predictions), offset)):
        if i >= max_i:
            break
        condition_icon = forecast.predictions[pidx].condition_icon
        display.scroll_raw64(LED8x8ICONS[condition_icon], i)



# -------------------------------------------------------------------------------
#  M A I N
# -------------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'climacell_cfg.json'
    apikey, lat, lon = read_config(filename)
    display = LEDDisplay()
    reset_display(display)
    forecast = get_climacell_forecast(apikey, lat, lon)
    print_forecast(forecast)
    last_fetched = datetime.now()
    i = 0
    while True:
        try:
            elapsed = datetime.now() - last_fetched
            timeout = 60 * 5 if (forecast is None) else 60 * 60
            if elapsed.total_seconds() >= timeout:
                print('Fetching new forecast')
                last_fetched = datetime.now()
                forecast = get_climacell_forecast(apikey, lat, lon)
                print_forecast(forecast)

            if i == 0 or forecast is None:
                display_clock(display)
            elif i == 1:
                display_current_forecast(display, forecast)
            elif i == 2:
                display_8_hr_forecast(display, forecast)

            time.sleep(2)

            i += 1
            i %= 3
        except Exception as e:
            print('unhandled exception', e)
