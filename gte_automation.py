import logging
import json
import re
import calendar
import time as timer
import sys
from pprint import pprint
from datetime import datetime
import webdriverautos as wd
import tsprocessing as ts

# define some globls
week_total_hours = ''
run_browser = False
day_summary = {}
page_wait_for_rows = 2
just_do_data_check = '--check' in sys.argv
driver = ''

def update_mode():
    if len(sys.argv) and '--continue' in sys.argv:
        return True
    return False

timesheet_entries = ts.get_time_entries()
timesheet_mapping = ts.get_time_mapping()
ts.sanity_check_input(timesheet_entries, timesheet_mapping)

day_map = ts.map_time_entries_by_day(timesheet_entries)
consolidated_day_map = ts.get_consolidated_day_map(day_map)
ts.sanity_check_calcs(consolidated_day_map, timesheet_mapping)

week_total_hours = ts.summarize_the_week(consolidated_day_map)

if not just_do_data_check:
    print(":Kicking off automation")
    driver = wd.get_driver()
    print(":logging in...")
    driver = wd.login(driver)
    driver = wd.change_period(driver,timesheet_entries, page_wait_for_rows)
    driver = wd.check_empty(driver)
    # fill out the time matrix (first page)
    unique_buckets_for_week = wd.run_gte_time_matrix(driver, timesheet_mapping, consolidated_day_map)

    # recalc one more time.
    wd.recalculate(driver)
    timer.sleep(wd.get_sleep_time())

    # check totals
    wd.check_totals(driver, week_total_hours)

    # we have verified our totals, let's save and move on
    wd.run_gte_time_detail_entries(driver, timesheet_entries, timesheet_mapping)

    #save the timesheet for now (no submit)
    elem = wd.find_button(driver, 'Save')
    elem.click()
    timer.sleep(page_wait_for_rows)

    wd.check_success(driver)
    '''
    Set a breakpoint on the driver.quit() line if you want to play with
    and then manually submit it.  This script will not automatically submit it.
    '''
    driver.quit()
else:
    print('Data check only, not running actual timesheet')
