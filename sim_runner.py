import json
import datetime
from plant_model import Plant

def _load_file(fname):
    with open(fname) as f:
        return json.load(f)

def default_env_conditions(co2_concentration):
    return {"air_temp_max": 30,
            "air_temp_min": 20,
            "snow_height": 0,
            "soil_water": 1000,
            "total_radiation": 20,
            "co2_concentration": co2_concentration,
            "day_length": 16}


def sim_runner(year=1979, co2_concentration=350):

    # Initialize weather data
    weather_data = _load_file('data_files/weather_data_colorado.json')
    labels = weather_data.pop(0)
    units = weather_data.pop(0)
    weather_data = [d for d in weather_data if str(d[0]) == str(year)]
    if len(weather_data) == 0:
        raise Exception("No data found for given year")
    ny = datetime.date.fromisoformat(f'{year}-01-01')
    sow_date = datetime.date.fromisoformat(f'{year}-05-22')
    sow_julian = sow_date - ny
    def get_weather_data(step_day):
        step_julian = sow_julian + datetime.timedelta(days=(step_day))
        step_data = weather_data[step_julian.days - 1]
        step_dict = {key: value for (key, value) in zip(labels, step_data)}
        return step_dict
    def get_env_conditions(step_day, co2_concentration):
        weather_data = get_weather_data(step_day)
        return {'air_temp_max': float(weather_data['maxt']),
                'air_temp_min': float(weather_data['mint']),
                'snow_height': float(weather_data['snow']),
                'soil_water': 1e10,
                'total_radiation': float(weather_data['radn']),
                'co2_concentration': co2_concentration,
                'day_length': float(weather_data['dayL'])}

    wheat_data = _load_file('data_files/wheat_data.json')
    env_data = _load_file('data_files/env_data.json')
    wheat_plant = Plant(wheat_data, env_data)
    day = 0
    while True:
        env_conditions = get_env_conditions(day, co2_concentration)
        wheat_plant.step(env_conditions)
        if wheat_plant.phase_name.startswith('harvest'):
            break
        day += 1
    logs = wheat_plant.get_logs()
    return logs
