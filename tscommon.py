def get_bucket_for_project_code(timesheep_mapping, project_code):
    for x in timesheep_mapping:
        mapping = timesheep_mapping.get(x)
        if mapping.get('Project Details') == project_code:
            return x