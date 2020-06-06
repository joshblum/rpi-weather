#!/usr/bin/env python
# ===============================================================================
# weather.py
#
# Get weather forecast from NOAA and display as 8x8 icons
#   * NOAA's doc: http://digital.weather.gov/xml/rest.php
#   * Set location using zipcode
#   * Use 12+hourly format
#   * Somewhat generalized for any number of days
#
# 2014-09-14
# Carter Nelson
# ===============================================================================
import datetime
import httplib
import time
import random
import sys
from collections import namedtuple
from xml.dom.minidom import parseString

from led_disp import LEDDisplay
from clock import display_clock
from led8x8icons import LED8x8ICONS

icons = ['SUNNY', 'RAIN', 'CLOUD', 'SHOWERS', 'SNOW', 'STORM']
synonym_map = {
    'SUNNY': ['CLEAR'],
    'RAIN': [],
    'CLOUD': ['AREAS FOG'],
    'SHOWERS': [],
    'SNOW': [],
    'STORM': [],
}

ZIPCODE = 11225
NUM_DAYS = 1
NOAA_URL = "digital.weather.gov"
REQ_BASE = r"/xml/sample_products/browser_interface/ndfdBrowserClientByDay.php?"
TIME_FORMAT = "12+hourly"
HEADERS = {"User-Agent": "Mozilla/5.0"}
Forecast = namedtuple(
    'Forecast', ['maximum', 'minimum', 'conditions', 'condition_icon'])


def validate_zip(zip_arg):
    """Return integer conversion of supplied string if valid, global default ZIPCODE otherwise."""
    try:
        zip = int(zip_arg)
        if zip < 99999 and zip > 0 and len(zip_arg) == 5:
            return zip
    except ValueError:
        pass
    return ZIPCODE


def get_offset():
    """ Returns 0 if local time after 6AM and before 6PM, 1 otherwise."""
    hour = time.localtime().tm_hour
    if hour > 6 and hour < 18:
        return 0
    else:
        return 1


def make_noaa_request():
    """Make request to NOAA REST server and return data."""
    REQUEST = REQ_BASE + "zipCodeList={0:05d}&".format(ZIPCODE) +\
        "format={0}&".format(TIME_FORMAT) +\
        "numDays={0}".format(NUM_DAYS)
    try:
        conn = httplib.HTTPSConnection(NOAA_URL)
        conn.request("GET", REQUEST, headers=HEADERS)
        print(NOAA_URL + REQUEST)
        resp = conn.getresponse()
        data = resp.read()
    except:
        return None
    else:
        return data


def get_noaa_forecast():
    """Return a string of forecast results."""
    try:
        res = parseString(make_noaa_request())
        conditions = res.getElementsByTagName('weather-conditions')
        temps = res.getElementsByTagName("temperature")
    except Exception as e:
        print(e)
        return None

    if '12' in TIME_FORMAT:
        offset = get_offset()
    else:
        offset = 0

    tempDict = {}
    for i, e in enumerate(temps):
        typ = str(e.getAttribute('type'))
        value = e.getElementsByTagName('value')
        if not len(value):
            continue
        val = int(value[0].firstChild.nodeValue)
        tempDict[typ] = val

    if not len(tempDict):
        return None
    if 'minimum' in tempDict and 'maximum' not in tempDict:
        tempDict['maximum'] = tempDict['minimum']
    elif 'maximum' in tempDict and 'minimum' not in tempDict:
        tempDict['minimum'] = tempDict['maximum']

    condition_icon = 'UNKNOWN'
    if len(conditions) > 0:
        condition = [e.getAttribute("weather-summary")
                     for e in conditions[offset::2]][0]
        condition_icon = normalize_daily_forecast(condition)
        if condition_icon == 'UNKNOWN':
            print 'condition:', condition.encode('ascii', 'ignore').upper()

    return Forecast(conditions=conditions, condition_icon=condition_icon, **tempDict)


def print_forecast(forecast=None):
    """Print forecast to screen."""
    if forecast is None:
        print 'null forecast'
        return
    print '-' * 20
    print time.strftime('%Y/%m/%d %H:%M:%S')
    print "ZIPCODE {0}".format(ZIPCODE)
    print '-' * 20
    print 'Condition: {}, Hi: {}, Lo: {}, Conditions: {}'.format(forecast.condition_icon, forecast.maximum, forecast.minimum, forecast.conditions)


def normalize_daily_forecast(condition):
    condition = condition.encode('ascii', 'ignore').upper()
    for icon, synonyms in synonym_map.items():
        if icon in condition:
            return icon
        for synonym in synonyms:
            if synonym in condition:
                return icon
    print 'Missing icon for daily forecast', condition
    return 'UNKNOWN'


def display_forecast(display, forecast=None, show_hi=True):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast == None:
        return

    i = 0
    display.scroll_raw64(LED8x8ICONS[forecast.condition_icon], i)

    i = 1
    icon = 'UP_ARROW' if show_hi else 'DOWN_ARROW'
    display.scroll_raw64(LED8x8ICONS[icon], i)

    temp = forecast.maximum if show_hi else forecast.minimum
    digits = []
    while temp > 0:
        new_d = temp % 10
        digits.append(new_d)
        temp /= 10
    offset = 2
    for i, d in enumerate(reversed(digits)):
        display.scroll_raw64(LED8x8ICONS['{0}'.format(d)], i + offset)


def display_msg(display, msg, delay):
    for i, char in enumerate(msg):
        idx = i % 4
        icon = char.upper().strip()
        if icon == '':
            icon = 'ALL_OFF'
        display.scroll_raw64(LED8x8ICONS[icon], idx, delay)



# -------------------------------------------------------------------------------
#  M A I N
# -------------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        ZIPCODE = validate_zip(sys.argv[1])

    display = LEDDisplay()
    reset_display(display)
    forecast = get_noaa_forecast()
    print_forecast(forecast)
    last_fetched = datetime.datetime.now()
    show_hi = True
    i = 0
    while True:
        try:
            elapsed = datetime.datetime.now() - last_fetched
            timeout = 60 * \
                5 if (forecast is None or not len(
                    forecast.conditions)) else 60 * 60
            if elapsed.total_seconds() >= timeout:
                print 'Fetching new forecast'
                last_fetched = datetime.datetime.now()
                forecast = get_noaa_forecast()
                print_forecast(forecast)

            if i == 0 or forecast is None:
                display_clock(display)
            else:
                display_forecast(display, forecast, show_hi=show_hi)
                show_hi = not show_hi
            time.sleep(2)

            i += 1
            i %= 3
        except Exception as e:
            print('unhandled exception', e)
