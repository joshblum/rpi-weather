import datetime
from weather import reset_display, get_noaa_forecast

#-------------------------------------------------------------------------------
#  M A I N
#-------------------------------------------------------------------------------

def display_forecast(forecast=None):
    """Display forecast as icons on LED 8x8 matrices."""
    if forecast == None:
        return
    display.scroll_raw64(LED8x8ICONS[forecast.condition_icon], 0)

if __name__ == "__main__":
    reset_display()
    forecast = get_noaa_forecast()
    print_forecast(forecast)
    while True:
        try:
            timeout = 60*5 if (forecast is None or not len(forecast.conditions)) else 60*60
            print 'Fetching new forecast'
            forecast = get_noaa_forecast()
            print_forecast(forecast)
            display_forecast(forecast)
            time.sleep(timeout)
        except Exception as e:
            print('unhandled exception', e)
