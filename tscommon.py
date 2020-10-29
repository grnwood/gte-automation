import tscommon
import re

date_heading_matcher = re.compile(r"\d\d?\/\d\d?")
gte_task_matcher = re.compile('\d{9}')

def get_bucket_for_project_code(timesheep_mapping, project_code):
    for x in timesheep_mapping:
        mapping = timesheep_mapping.get(x)
        if mapping.get('Project Details') == project_code:
            return x

def find_detail_lines_for_date_and_task( dateLine, task, timesheet_entries, timesheet_mapping):
    lines = ''
    flag = False
    str_line = ''
    # make sure we get only the task # portion out.
    if len(task) > 9:
        grp = gte_task_matcher.match(task)
        if grp:
            task = grp.group()

    bucket = tscommon.get_bucket_for_project_code(timesheet_mapping, task)
    if not bucket:
        raise ValueError("could not find bucket for project code: "+task)

    for str_line in timesheet_entries:
        # found a date heading?
        if tscommon.date_heading_matcher.match(str_line):
            # the date heading we want? then set a flag
            if dateLine in str_line:
                flag = True
            else:
                flag = False
            continue
        if flag:
            line_parts = str_line.split(',')
            if not len(line_parts) == 3:
                continue
            if line_parts[0] == bucket:
                lines = lines + line_parts[1].strip() + ' (' + line_parts[2].strip()+ ') \n'
    return lines