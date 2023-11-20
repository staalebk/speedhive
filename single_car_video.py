#!/usr/bin/env python3
import pandas as pd
from moviepy.editor import concatenate_videoclips, TextClip, ColorClip

# Load the CSV file
csv_file = 'input.csv'
df = pd.read_csv(csv_file)

# Convert lap times to seconds including milliseconds
def convert_time_to_seconds(time_str):
    parts = time_str.split(':')
    seconds = float(parts[-1])
    if len(parts) > 1:
        seconds += int(parts[-2]) * 60
    return seconds

# Function to format seconds back into 'minutes:seconds.milliseconds'
def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes}:{seconds:06.3f}" if minutes else f"{seconds:05.3f}"

df['Lap Time'] = df['Lap Time'].apply(convert_time_to_seconds)

# Initialize an array to hold text clips and variables for best lap time and cumulative time
text_clips = []
best_lap_time = float('inf')
cumulative_time = 0.0

# Create and configure text clips
for index, row in df.iterrows():
    # Update the best lap time if current lap time is lower
    best_lap_time = min(best_lap_time, row['Lap Time'])

    formatted_lap_time = format_time(row['Lap Time'])
    formatted_best_lap_time = format_time(best_lap_time)

    text = f"Lap: {row['Lap']} Pos: {row['Pos']+1} Last: {formatted_lap_time} Best: {formatted_best_lap_time} Avg Speed: {row['Speed']}"

    if index == len(df) - 1:
        duration = 60  # Duration for last lap
    else:
        duration = df.at[index + 1, 'Lap Time']

    txt_clip = TextClip(text, fontsize=70, color='white', font='Amiri-Bold', bg_color='black', size=(2400, 100), method='caption', align='West')
    txt_clip = txt_clip.set_duration(duration).set_start(cumulative_time)
    text_clips.append(txt_clip)

    cumulative_time += row['Lap Time']

# Concatenate text clips to form a single video
final_video = concatenate_videoclips(text_clips, method="compose")

# Write the result to a file with specified fps
final_video.write_videofile("race_info_text_video.mp4", fps=29.97)
