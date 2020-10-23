import logging
import json
import re
import calendar
import time as timer
import sys
from pprint import pprint
from datetime import datetime

matcher = re.compile(r"\d\d?\/\d\d?")
print_summary_only = True

def get_time_mapping():
    # load file
    mappings = {}
    f = open('time-mapping.json', 'r')
    mappings = json.load(f)
    f.close()
    return mappings
 
def get_time_entries():
    # load entires
    entries = []
    f = open('time-entries.txt', 'r')
    entries = f.readlines()
    f.close()
    return entries

def map_time_entries_by_day(timesheet_lines):
    """
    This should consolidate each day into a map by day
    """
    day_map = {}
    cur_day_lines = []
    cur_day = ''
    for line in timesheet_lines:
        if 'period' in line:
            continue
        line = line.strip()
        if not line:
            continue
        if matcher.match(line):
            if line in day_map:
                cur_day_lines = day_map.get(line)
            else:
                print("new day: "+line)
                cur_day = line
                day_map[line] = []
                cur_day_lines = day_map.get(line)
        else:
            cur_day_lines.append(line)
        day_map[cur_day] = cur_day_lines
    return day_map

def consolidate_time_entries_per_day(timesheet_lines):
    '''
    This method looks to summarize the time buckets by day
    '''
    map_of_buckets = {}
    map_of_desc = {}
    for line in timesheet_lines:
        if 'period' in line:
            continue
        if len(line.strip()) > 0:
            fields = line.split(',')
            key = fields[0]
            time = fields[2]
            desc = fields[1]
            time_desc = desc + ' ('+time+')\n'
            if key in map_of_buckets:
                val = int(map_of_buckets.get(key))
                val = val + int(time)
                map_of_buckets[key] = val
            else:
                map_of_buckets[key] = int(time)
            if key in map_of_desc:
                descs = map_of_desc.get(key)
                descs = descs + time_desc
                map_of_desc[key] = descs
            else:
                map_of_desc[key] = time_desc
    return {'map_of_buckets': map_of_buckets, 'map_of_desc': map_of_desc}

def sanity_check_input(timesheet_entries, timesheet_mapping):
    # make sure we have at least some data
    assert len(timesheet_entries) > 0
    assert len(timesheet_mapping) > 0

    # sanity check in bound data is three cols
    line = 0
    for tline in timesheet_entries:
        line += 1
        try: 
            assert (len(tline.split(',')) == 3 or len(tline.strip()) == 0 \
                or matcher.match(tline.strip()) or 'period' in tline)
        except:
            raise Exception('bad line #'+str(line))

def get_consolidated_day_map(day_map):
    consolidated_day_map = {}

    for key in day_map.keys():
        tlines = day_map.get(key)
        totals = consolidate_time_entries_per_day(tlines)
        consolidated_day_map[key] = totals.get('map_of_buckets')
        consolidated_day_map[key+'-desc'] = totals.get('map_of_desc')

    return consolidated_day_map

# gather summaries


def summarize_the_week(consolidated_day_map):
    day_summary = []
    total = 0
    week_total = 0
    for key in consolidated_day_map:
        if '-desc' not in key:
            day_total = 0
            buckets = consolidated_day_map.get(key)
            entries = []
            for sttKey in buckets:
                curtotal = int(buckets.get(sttKey))
                total = total + curtotal
                day_total = day_total + curtotal
                entries.append(sttKey+'( '+str(curtotal) +
                               ' mins / ' + str(curtotal/60) + ' hours)')
                entries[0] = "== "+key + " == day total ("+str(
                    day_total)+" mins / " + str(day_total/60) + " hours) =="
            week_total = week_total + day_total
            day_summary.append(entries)

    week_total_hours = str(week_total/60)
    if print_summary_only:
        pprint(day_summary)
        print()
        print("Week total: "+str(week_total) +
              ' mins ' + str(week_total/60) + ' hours')
        exit
    return week_total_hours


def sanity_check_calcs(summary_time_totals, timesheet_mapping):
    # sanity check each key in the summary against the map.
    for key in summary_time_totals:
        for sttKey in summary_time_totals.get(key):
            if not '-desc' in sttKey and sttKey not in timesheet_mapping:
                raise ValueError('You have time entry key ('+sttKey + \
                     ') that is not in timesheet mapping.  Please update.')
