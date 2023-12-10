import datetime
from weather import reset_display, get_noaa_forecast, display_clock, display_forecast, print_forecast

# -------------------------------------------------------------------------------
#  M A I N
# -------------------------------------------------------------------------------
if __name__ == "__main__":
    reset_display()
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
            if elapsed.total_seconds() >= timeout :
                print 'Fetching new forecast'
                last_fetched = datetime.datetime.now()
                forecast = get_noaa_forecast()
                print_forecast(forecast)

            if i == 0 or forecast is None:
                display_clock()
            else:
                display_forecast(forecast, show_hi=show_hi)
                show_hi = not show_hi
            time.sleep(2)

            i += 1
            i %= 3
        except Exception as e:
            print('unhandled exception', e)
