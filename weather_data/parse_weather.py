import json

def parse_met_to_json(fpath, output_name):
    with open(fpath) as f:
        weather = f.read()
    lines = weather.splitlines()
    lines = lines[10:]
    lists = [line.split() for line in lines]
    with open(f'data_files/{output_name}', 'w') as f:
        json.dump(lists, f)
