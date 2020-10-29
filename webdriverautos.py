import logging
import json
import re
import calendar
import time as timer
import sys
import tscommon
import tsprocessing
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By


sleep_seconds_between_ops = 1

def get_sleep_time():
    return sleep_seconds_between_ops

def change_period(driver, timesheet_entries, page_wait_for_rows):
    # check if we are dealing with a different period
    if 'period' in timesheet_entries[0] and len(timesheet_entries[0].split('=')) == 2:
        elem = driver.find_elements_by_tag_name('select')[0]
        period = timesheet_entries[0].split('=')[1]
        print("Setting period of timesheet to: "+period)
        elem.send_keys(period)
        timer.sleep(page_wait_for_rows)
    return driver

def check_empty(driver):
    # Don't work on a timesheet that already has data saved in it unless we are in update mode!
    if driver.find_element_by_xpath('//*[@id="B22_1_0"]').get_attribute('value'):
        raise Exception("Warning!  Detected a already saved timesheet \
            NOT proceeding.")
    return driver

def check_success(driver):
    # make sure it saved
    if not 'The timecard has been saved successfully.' in driver.page_source:
        raise ValueError("Warning, did not detect the timesheet was saved, check it!")

def get_driver():
    opts = webdriver.FirefoxOptions()
    opts.add_argument("--width=1400")
    opts.add_argument("--height=700")
    driver = webdriver.Firefox(options=opts)
    #driver = webdriver.Firefox()
    #driver.set_window_size(1400,700)
    return driver
    
def login(driver):
    user = ''
    password = ''
    try:
        creds = open('credentials.txt','r')
        line = creds.readline()
        user = line.split('=')[1]
        line = creds.readline()
        password = line.split('=')[1]
        creds.close()
    except:
        raise ValueError("Some issue with your password file 'credentials.txt', please fix")

    driver.get("https://upp.capgemini.com/")
    #assert "Python" in driver.title
    try:
        ssourl = EC.url_contains("sspoam.capgemini.com")
        WebDriverWait(driver, 20).until(ssourl)
    except:
        print("Timed out waiting for SSO url")
        raise "SSO timeout"

    btn = driver.find_element_by_css_selector("body > button:nth-child(2)")
    btn.click()

    try:
        ec = EC.title_contains("Oracle Access Management")
        WebDriverWait(driver, 10).until(ec)
    except:
        print("Timed out waiting on Oracle login page")
        raise "No oracle page"

    elem = driver.find_element_by_xpath("//*[@id=\"username\"]")
    elem.send_keys(user)
    elem = driver.find_element_by_xpath("//*[@id=\"password\"]")
    elem.send_keys(password)
    elem.send_keys(Keys.RETURN)
    try:
        ec = EC.url_contains("upp.capgemini.com/OA_HTML")
        wait = WebDriverWait(driver, 20).until(ec)
    except:
        print("Timed out waiting on GTE main page")
        raise "No GTE main page page"

    driver.get("https://upp.capgemini.com/OA_HTML/RF.jsp?function_id=16744&resp_id=71369&resp_appl_id=809&security_group_id=0&lang_code=US&oas=ZyZNPnozfgJIWQBaFio13Q..&params=avwQ4Zpumqk4wM2hnLSEtfVRURgrCch9rnGvV9mMQIc")
    return driver

def get_gte_element(name, row):
    # map of relevant xpath keys we are targeting

    gte_xpath_map = {
        "Period": '//*[@id="N77"]',
        "Project Details": '//*[@id="A24!row!N1display"]',
        "Task Details": '//*[@id="A25!row!N1display"]',
        "Type": '//*[@id="A26!row!N1display"]',
        "Site": '//*[@id="A27!row!N1"]',
        "Location": '//*[@id="A28!row!N1display"]',
        "Approver": '//*[@id="A37!row!N1"]',
        "Monday": '//*[@id="B22_!row!_0"]',
        "Tuesday": '//*[@id="B22_!row!_1"]',
        "Wednesday": '//*[@id="B22_!row!_2"]',
        "Thursday": '//*[@id="B22_!row!_3"]',
        "Friday": '//*[@id="B22_!row!_4"]',
        "Saturday": '//*[@id="B22_!row!_5"]',
        "Sunday": '//*[@id="B22_!row!_6"]',
        "Add Another Row": "/html/body/div[5]/form/span[2]/div[3]/div/div[1]/div/div[3]/div[1]/div[2]/span[1]/span/table[1]/tbody/tr/td/table[2]/tbody/tr[5]/td/table/tbody/tr[6]/td[2]/table/tbody/tr[3]/td[1]/table/tbody/tr/td[1]/button"
    }

    val = gte_xpath_map.get(name)
    val = val.replace('!row!', str(row))
    return val

def run_gte_time_matrix(driver, timesheet_mapping, consolidated_day_map):
    # loop all the unique buckets I will have for this week
    '''
    {'8/31': {'citta': 60,
          'clubs': 195,
          'cush': 30,
          'dartpdp': 30,
          'int': 45,
          'lead': 15,
          'sales': 120},
        '9/1': {'bbwinapp': 15,
    '''
    unique_buckets_for_week = []
    for key in consolidated_day_map.keys():
        buckets = consolidated_day_map.get(key)
        for sttKey in buckets:
            if sttKey not in unique_buckets_for_week:
                unique_buckets_for_week.append(sttKey)
    gte_rows = len(unique_buckets_for_week)
    buckets_encountered = []
    print("will need "+str(gte_rows)+" rows in gte")

    # get global entry descriptions
    globalmap = timesheet_mapping.get('global')
    row = 0
    sttKeys = {}
    for key in consolidated_day_map.keys():
        if not '-desc' in key:
            datestring = key
            if (len(datestring) <= 5):
                # assume 2020
                datestring = datestring + "/2020"
            curdate = datetime.strptime(datestring, '%m/%d/%Y')
            weekday = calendar.day_name[curdate.weekday()]
            print("\t+-- for day: "+str(curdate)+" ("+weekday+")")

            buckets = consolidated_day_map.get(key)
            for sttKey in buckets:
                print("\t\t+-- working on bucket for "+sttKey)
                newline_added = False
                if sttKey in timesheet_mapping:
                    mapping = timesheet_mapping.get(sttKey)
                    time = buckets[sttKey]
                    if sttKey not in buckets_encountered:
                        if row >= 1:
                            #elem = find_button(driver,'Add Another Row')
                            # elem.click()
                            row = row + 1
                            # try:
                            # timer.sleep(sleep_seconds_between_ops)
                            #WebDriverWait(driver, page_wait_for_rows).until(EC.visibility_of_element_located((By.XPATH, get_gte_element('Project Details',row))))
                            # except:
                            # app is wonkey, maybe try again?
                            #elem = find_button(driver,'Add Another Row')
                            # elem.click()
                            # timer.sleep(sleep_seconds_between_ops)
                            #WebDriverWait(driver, page_wait_for_rows).until(EC.visibility_of_element_located((By.XPATH, get_gte_element('Project Details',row))))
                            sttKeys[sttKey] = row
                            newline_added = True

                        if row == 0 or newline_added:
                            #{'Project Details': '100680532', 'Task Details': 'Technical Architecture'}
                            if row == 0:
                                row = 1
                                sttKeys[sttKey] = 1

                            task = mapping.get('Project Details')
                            details = mapping.get('Task Details')
                            approver = globalmap.get('Approver')
                            location = globalmap.get('Location')
                            site = globalmap.get('Site')

                            tasktype = globalmap.get('Type')
                            elem = driver.find_element_by_xpath(
                                get_gte_element('Type', row))
                            
                            elem.send_keys(tasktype)
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            elem = driver.find_element_by_xpath(
                                get_gte_element('Site', row))
                            elem.send_keys(site)
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            elem = driver.find_element_by_xpath(
                                get_gte_element('Location', row))
                            elem.send_keys(location)
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            timer.sleep(sleep_seconds_between_ops)
                            elem = driver.find_element_by_xpath(
                                get_gte_element('Approver', row))
                            elem.send_keys(approver)
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            elem = driver.find_element_by_xpath(
                                get_gte_element(weekday, row))
                            elem.send_keys(str(time/60))
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            elem = driver.find_element_by_xpath(
                                get_gte_element('Project Details', row))
                            elem.send_keys(task)
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            timer.sleep(sleep_seconds_between_ops)
                            elem = driver.find_element_by_xpath(
                                get_gte_element('Task Details', row))
                            elem.send_keys(details)
                            webdriver.ActionChains(
                                driver).send_keys(Keys.TAB).perform()
                            timer.sleep(sleep_seconds_between_ops)
                            timer.sleep(sleep_seconds_between_ops)
                            recalculate(driver)
                    else:
                        existingRow = sttKeys[sttKey]
                        elem = driver.find_element_by_xpath(
                            get_gte_element(weekday, existingRow))
                        elem.send_keys(str(time/60))
                        timer.sleep(sleep_seconds_between_ops)
                        # recalculate(driver)
                    buckets_encountered.append(sttKey)
                else:
                    raise ValueError("ran across a key I have no mapping for.")
    return unique_buckets_for_week

def find_detail_link(driver, index):
    details_image = 'detailsicon_enabled.gif'
    details = driver.find_elements_by_css_selector('.x1x > a > img')
    iteration = 0
    for det in details:
        if details_image in det.get_attribute('src'):
            if index == iteration:
                return det
            iteration = iteration + 1


def get_detail_entries(consolidated_day_map, index):
    iteration = 0
    for key in consolidated_day_map:
        if '-desc' in key:
            if iteration == index:
                return consolidated_day_map.get(key)
            iteration = iteration + 1
 
def run_gte_time_detail_entries(driver,timesheet_entries, timesheet_mapping):
    print('Filling in task details')

    rows = 0
    while detail := find_detail_link(driver, rows):
        print('Entering detail records for GTE row #'+str(rows))
        rows = rows + 1
        detail.click()
        timer.sleep(2)
        # the the task from the page
        task = driver.find_element_by_css_selector('.x1t .xiz').text
        days = driver.find_elements_by_css_selector('.x7p')
        for counter, day in enumerate(days):
            dayStringParse = days[counter].text.split(':')[1].strip().split(',')
            dayStringParse[1] = dayStringParse[1].strip()
            dayStringParse[2] = dayStringParse[2].strip()
            parsedDate = datetime.strptime(dayStringParse[1] + ' ' + dayStringParse[2], '%B %d %Y')
            dateLine = parsedDate.strftime('%m/%d')
            dateLine = str(int(dateLine.split('/')[0])) + '/' + str(int(dateLine.split('/')[1]))
            tb = driver.find_elements_by_tag_name('textarea')[counter]
            tb.send_keys(tscommon.find_detail_lines_for_date_and_task(dateLine,task,timesheet_entries, timesheet_mapping))
        find_button(driver, 'Apply').click()
    


def find_button(driver, name):
    elems = driver.find_elements_by_css_selector('.x80')
    for button in elems:
        if button.text == name:
            return button
    return None


def check_totals(driver, total_hours):
    total = driver.find_element_by_css_selector('td.x26:nth-child(9) > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(3) > span:nth-child(1)')
    hours = total.text
    if float(hours) != float(total_hours):
        raise ValueError("Warning detected only "+hours +
                         " hours but timesheet has: "+total_hours)

def recalculate(driver):
    # let's make sure it's fully recalculated
    elem = find_button(driver, 'Recalculate')
    elem.click()
    timer.sleep(get_sleep_time())

