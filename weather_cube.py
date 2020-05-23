import datetime
import time
from weather import reset_display, get_noaa_forecast, print_forecast, display_cube

#-------------------------------------------------------------------------------
#  M A I N
#-------------------------------------------------------------------------------


if __name__ == "__main__":
    reset_display()
    while True:
        try:
            forecast = get_noaa_forecast()
            timeout = 60*5 if (forecast is None or not len(forecast.conditions)) else 60*60
            print 'Fetching new forecast'
            print_forecast(forecast)
            display_cube(forecast)
            time.sleep(timeout)
        except Exception as e:
            print('unhandled exception', e)
