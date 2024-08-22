import json
from datetime import datetime
import pytz

def convert_datetime_format(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.date().isoformat()  # Return just the date if needed
    except ValueError:
        return date_str

def process_json_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def process_data(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, str) and 'T' in v:
                    d[k] = convert_datetime_format(v)
                elif isinstance(v, (dict, list)):
                    process_data(v)
        elif isinstance(d, list):
            for i in range(len(d)):
                if isinstance(d[i], str) and 'T' in d[i]:
                    d[i] = convert_datetime_format(d[i])
                elif isinstance(d[i], (dict, list)):
                    process_data(d[i])

    process_data(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# Specify the input and output file paths
process_json_file('data.json', 'converted_data.json')
