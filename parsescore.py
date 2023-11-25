#!/usr/bin/env python3
import os, time
import pandas as pd
from datetime import timedelta
import pprint, operator
import json

teams = {}

def timedelta_sleep(td):
    sleep_seconds = td.total_seconds()
    time.sleep(sleep_seconds)

def timedelta_to_str(td):
    # Converts a timedelta object to a string in the format 'HH:MM:SS.mmm'
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int(td.microseconds / 1000)  # Converting microseconds to milliseconds
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

# Function to convert lap time string to timedelta
def lap_time_to_timedelta(lap_time_str):
    try:
        if isinstance(lap_time_str, str):
            parts = lap_time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(float, parts)
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
            elif len(parts) == 2:
                minutes, seconds = map(float, parts)
                return timedelta(minutes=minutes, seconds=seconds)
            elif len(parts) == 1:
                seconds = float(parts[0])
                return timedelta(seconds=seconds)
    except Exception as e:
        print(f"Error processing lap time: {lap_time_str}. Error: {e}")
    return timedelta(0)

# Function to read and preprocess race data
def preprocess_race_data(directory):
    all_data = []
    for filename in os.listdir(directory):
        if not "Driftfun" in filename:
            continue
        team = {}
        team['pit_in'] = []
        team['pit_out'] = []
        team['lap_times'] = []
        team['lap_start'] = []
        team['race_end'] = []
        if filename.endswith('.csv'):
            team['name'] = filename.split(',')[0].strip()  # Assuming team name is before the first comma
            df = pd.read_csv(os.path.join(directory, filename))
            team['offset'] = df['Diff to P1'].iloc[:1].apply(lap_time_to_timedelta) + lap_time_to_timedelta("2:04.0")
            team['L1'] = df['Lap Time'].iloc[:1].apply(lap_time_to_timedelta)
            start_time = team['offset'][0] - team['L1'][0]
#            print(team['name'])
            # Convert lap times to timedelta
            lap_times = df['Lap Time'].apply(lap_time_to_timedelta)
            lap = 0
            pitstop = timedelta(minutes=4)
            maxlaptime = timedelta(minutes = 5, seconds=35) # minimum laptime to think this is a pit stop
            for index, laptime in lap_times.items():
                team['lap_start'].append(start_time)
                if (laptime > maxlaptime):
                    team['pit_in'].append(start_time + laptime - pitstop)
                    team['pit_out'].append(start_time + laptime)
                    team['lap_times'].append(laptime - pitstop)
                else:
                    team['lap_times'].append(laptime)
                start_time += laptime
            team['race_end'].append(start_time)
            all_data.append(team)
    return all_data

# Function to calculate the frames at which updates occur
def calculate_update_frames(data):
    update_frames = []
    running_time = 0
    for _, row in data.iterrows():
        lap_time_seconds = row['Lap Time'].total_seconds()
        frames_for_lap = int(lap_time_seconds * FPS)
        running_time += frames_for_lap
        update_frames.append(running_time)
    return update_frames

def first_event(team):
    first = timedelta(hours=69)
    if len(team['lap_start']):
        first = team['lap_start'][0]
    if len(team['pit_in']) and team['pit_in'][0] < first:
        first = team['pit_in'][0]
    if len(team['race_end']) and team['race_end'][0] < first:
        first = team['race_end'][0]
    return first

def print_score():
    #This should print the current status of the teams variable, sorted by 'lap' and who 'lastround'
    print("--------- Score: ")
     # Sort teams by 'lap' in descending order and then by 'lastround' in ascending order
    sorted_teams = sorted(teams.items(), key=lambda x: (-x[1]['lap'], x[1]['lastround']))
    place = 1
    for team_name, team_info in sorted_teams:
        print(f"{place} {team_name}, Lap: {team_info['lap']}, Last Round: {team_info['lastround']}, In Pit: {'Yes' if team_info['in_pit'] else 'No'}, Finished: {'Yes' if team_info['finish'] else 'No'}")
        place += 1

def gen_json_obj():
    sorted_teams = sorted(teams.items(), key=lambda x: (-x[1]['lap'], x[1]['lastround']))

    # Convert the sorted teams list into a format that's serializable to JSON
    json_ready_teams = []
    for team_name, team_info in sorted_teams:
        # Convert timedelta objects to strings
        json_ready_teams.append(team_info)

    return json.loads(json.dumps(json_ready_teams))

def generate_data(data):
    series = []
    first = timedelta(hours=69)
    for team in data:
        if first_event(team) < first:
            first = first_event(team)
    last = timedelta(0)
    while first < timedelta(hours=68):
#        timedelta_sleep(first-last)
        last = first
        for team in data:
            if first_event(team) == first:
                name = team['name']
                if name not in teams:
#                    print("Creating " + name)
#                    print(first)
                    teams[name] = {}
                    teams[name]['name'] = name
                    teams[name]['lap'] = -1
                    teams[name]['pits'] = 0
                    teams[name]['in_pit'] = False
                    teams[name]['finish'] = False
                    teams[name]['current_lap_time'] = "0.0"
                    if "RMS Prospects" in name: # Fix missing transponder
                        teams[name]['lap'] += 8
                        teams[name]['pits'] = 1
                        teams[name]['in_pit'] = True
                if len(team['lap_start']) and first == team['lap_start'][0]:
                    teams[name]['lastround'] = timedelta_to_str(first)
                    teams[name]['lap'] += 1
                    teams[name]['last_lap_time'] = teams[name]['current_lap_time']
                    teams[name]['current_lap_time'] = timedelta_to_str(team['lap_times'][0])
                    teams[name]['in_pit'] = False
                    team['lap_start'].pop(0)
                    team['lap_times'].pop(0)
#                    print("New lap by " + name)
                if len(team['pit_in']) and first == team['pit_in'][0]:
                    teams[name]['in_pit'] = True
                    teams[name]['pits'] += 1
                    team['pit_in'].pop(0)
#                    print("Pitting: " + name)
                if len(team['race_end']) and first == team['race_end'][0]:
                    teams[name]['lap'] += 1
                    teams[name]['lastround'] = timedelta_to_str(first)
                    teams[name]['finish'] = True
                    team['race_end'].pop(0)
#                    print("Finish: " + name)
                #print(team['name'])
                #print(first)
#        print_score()
#        print(gen_json())
        d = {}
        d['time'] = timedelta_to_str(first)
        d['score'] = gen_json_obj()
        series.append(d)
        first = timedelta(hours=69)
        for team in data:
            if first_event(team) < first:
                first = first_event(team)
    with open("landskampen.json", "w") as outfile:
        outfile.write(json.dumps(series, indent=2))
#    print(gen_json())
#    print_score()

# Directory containing the CSV files
race_directory = 'race'

# Read and preprocess data
race_data = preprocess_race_data(race_directory)
generate_data(race_data)

# Calculate update frames
#update_frames = calculate_update_frames(race_data)
#print(update_frames)
#print(len(update_frames))
