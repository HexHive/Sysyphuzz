import re
import matplotlib.pyplot as plt
from datetime import datetime
import subprocess
import json
import os
import argparse
import numpy as np

# Function to read the log file and extract coverage values and seed load events
def extract_coverage_and_seeds(filename, crash_counts=None, global_crash_events=None, max_hours=float('inf'), crash_event_sources=None, is_boost=False):
    coverage_values = []
    time_values = []
    hitmap_time = None  # Stores the first 'Begin to analyze Hit Map' time
    hitmap_time_delta = None
    initial_timestamp = None
    local_hash = set()

    with open(filename, 'r') as file:
        for line in file:
            # Extract coverage value
            coverage_match = re.search(r'coverage=(\d+)', line)
            if coverage_match:
                timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    current_timestamp = datetime.strptime(timestamp_match.group(1), '%Y/%m/%d %H:%M:%S')
                    # Set the initial timestamp as the base time
                    if not initial_timestamp:
                        initial_timestamp = current_timestamp
                    # Calculate the time difference in hours from the initial timestamp
                    time_delta = (current_timestamp - initial_timestamp).total_seconds() / 3600  # Convert to hours

                    # Append the relative time (in hours) and coverage value
                    time_values.append(time_delta)
                    coverage_values.append(int(coverage_match.group(1)))

            # Detect the first "Begin to analyze Hit Map" line and extract the timestamp
            if not hitmap_time and "Begin to analyze Hit Map" in line:
                timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    hitmap_time = datetime.strptime(timestamp_match.group(1), '%Y/%m/%d %H:%M:%S')
                    hitmap_time_delta = (hitmap_time - initial_timestamp).total_seconds() / 3600

            if crash_counts is not None and global_crash_events is not None and 'crash:' in line:
                timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    current_timestamp = datetime.strptime(timestamp_match.group(1), '%Y/%m/%d %H:%M:%S')
                    time_delta = (current_timestamp - initial_timestamp).total_seconds() / 3600
                    if hitmap_time_delta is None:
                        continue
                    if (current_timestamp - hitmap_time).total_seconds() / 3600 > max_hours:
                        continue

                    crash_message = line.split('crash:', 1)[1].strip()
                    crash_hash = hash(crash_message)
                    
                    if crash_hash not in local_hash:
                        local_hash.add(crash_hash)
                        hex_crash_hash=hex(crash_hash)

                        if hex_crash_hash not in crash_event_sources:
                            crash_event_sources[hex_crash_hash] = {"message": crash_message, "boost": [], "original": []}

                        if crash_event_sources is not None:
                            if is_boost:
                                crash_event_sources[hex_crash_hash]["boost"].append(filename)
                            else:
                                crash_event_sources[hex_crash_hash]["original"].append(filename)


                    if crash_hash in global_crash_events:
                        continue
                    global_crash_events.add(crash_hash)
                    if "KASAN" in crash_message or "UBSAN" in crash_message:
                        crash_type = "SAN"
                    elif "kernel BUG" in crash_message:
                        crash_type = "kernel BUG"
                    elif "BUG:" in crash_message:
                        crash_type = "BUG"
                    #elif "WARNING" in crash_message:
                    #    crash_type = "WARNING"
                    elif "general protection fault" in crash_message:
                        crash_type = "general protection fault"
                    else:
                        continue
                    crash_counts[crash_type] += 1


    return time_values, coverage_values, hitmap_time_delta, initial_timestamp

# Function to compute min, max, and average coverage
def calculate_coverage_bounds(time_data, coverage_data, max_hours):
    max_steps = int(max_hours * 10)
    interval = max_hours / max_steps
    coverage_values = np.full((max_steps, len(time_data)), np.nan)

    for run_idx, (times, coverages) in enumerate(zip(time_data, coverage_data)):
        for t, c in zip(times, coverages):
            if t <= max_hours:  # **Only process values within max_hours**
                index = min(int(t / interval), max_steps - 1)
                coverage_values[index, run_idx] = c

    min_coverage = np.nanmin(coverage_values, axis=1)
    max_coverage = np.nanmax(coverage_values, axis=1)
    avg_coverage = np.nanmean(coverage_values, axis=1)
    avg_time_values = [i * interval for i in range(max_steps)]

    return avg_time_values, min_coverage, max_coverage, avg_coverage

# Function to calculate the average coverage values for each time step
#def calculate_average_coverage(time_data, coverage_data, max_hours):
#    extended_max_hours = max_hours + 2
#    max_steps = int(extended_max_hours * 10)  # Higher resolution for smoother lines
#    avg_coverage = np.zeros(max_steps)
#    counts = np.zeros(max_steps)
#    interval = extended_max_hours / max_steps

#    for times, coverages in zip(time_data, coverage_data):
#        for t, c in zip(times, coverages):
#            index = min(int(t / interval), max_steps - 1)
#            avg_coverage[index] += c
#            counts[index] += 1

#    avg_coverage = np.divide(avg_coverage, counts, out=np.zeros_like(avg_coverage), where=counts != 0)
#    avg_time_values = [i * interval for i in range(max_steps)]
    
#    return avg_time_values[:int(max_hours * 10)], avg_coverage[:int(max_hours * 10)]

# Function to compute the average Boost Hitmap Time
def compute_avg_hitmap_time(hitmap_times):
    valid_times = [t for t in hitmap_times if t is not None]
    if valid_times:
        return sum(valid_times) / len(valid_times)
    return None

# Plot the coverage values and crash events for the log files
def plot_coverage_with_crashes(boost_coverage_data, boost_time_data, boost_hitmap_times,
                               coverage_coverage_data, coverage_time_data, coverage_hitmap_times,
                               boost_crash_counts, coverage_crash_counts,
                               output_filename, max_hours):
    plt.figure(figsize=(12, 6))

    # Compute min, max, and avg for Boost and Coverage
    avg_boost_time, min_boost, max_boost, avg_boost = calculate_coverage_bounds(boost_time_data, boost_coverage_data, max_hours)
    avg_coverage_time, min_coverage, max_coverage, avg_coverage = calculate_coverage_bounds(coverage_time_data, coverage_coverage_data, max_hours)

    # Plot average coverage lines
    plt.plot(avg_boost_time, avg_boost, color='blue', linestyle='-', linewidth=2, label="SyzBoost Avg Coverage")
    plt.plot(avg_coverage_time, avg_coverage, color='orange', linestyle='-', linewidth=2, label="Syzkaller Avg Coverage")

    # **Fill between min and max with transparency**
    plt.fill_between(avg_boost_time, min_boost, max_boost, color='blue', alpha=0.15, label="SyzBoost Coverage Range", zorder=2)
    plt.fill_between(avg_coverage_time, min_coverage, max_coverage, color='orange', alpha=0.15, label="Syzkaller Coverage Range", zorder=1)

    # Plot shaded region for Boost
    #plt.fill_between(avg_boost_time, min_boost, max_boost, color='blue', alpha=0.2, label='Boost Coverage Range')
    #plt.plot(avg_boost_time, avg_boost, 'b-', linewidth=1.5, label='Avg Boost Coverage')

    # Plot shaded region for Coverage
    #plt.fill_between(avg_coverage_time, min_coverage, max_coverage, color='orange', alpha=0.2, label='Syzkaller Coverage Range')
    #plt.plot(avg_coverage_time, avg_coverage, 'o-', linewidth=1.5, label='Avg Coverage-Guided')

    # Define line styles
    #boost_style = {'color': 'blue', 'linestyle': '--', 'alpha': 0.5, 'label': 'Boost Coverage'}
    #coverage_style = {'color': 'orange', 'linestyle': '--', 'alpha': 0.5, 'label': 'Coverage-Guided Coverage'}
    #avg_boost_style = {'color': 'blue', 'linestyle': '-', 'linewidth': 1.5, 'label': 'Average Boost Coverage'}
    #avg_coverage_style = {'color': 'orange', 'linestyle': '-', 'linewidth': 1.5, 'label': 'Average Coverage-Guided Coverage'}

    # Plot each boost log with dashed lines
    # Compute the average Boost Hitmap Time
    avg_boost_hitmap_time = compute_avg_hitmap_time(boost_hitmap_times)
    if avg_boost_hitmap_time is not None and avg_boost_hitmap_time <= max_hours:
        plt.axvline(x=avg_boost_hitmap_time, color='blue', linestyle=':', linewidth=1, label='Avg Corpus Replay Finished Time (SyzBoost).')
    #for idx, (time_values, coverage_values) in enumerate(zip(boost_time_data, boost_coverage_data)):
        #plt.plot(time_values, coverage_values, linestyle='--', color='blue', alpha=0.5, 
                #label="Boost Coverage" if idx == 0 else None)

    # Plot each coverage-guided log with dashed lines
    avg_coverage_hitmap_time = compute_avg_hitmap_time(coverage_hitmap_times)
    if avg_coverage_hitmap_time is not None and avg_coverage_hitmap_time <= max_hours:
        plt.axvline(x=avg_coverage_hitmap_time, color='orange', linestyle=':', linewidth=1, label='Avg Corpus Replay Finished Time (Syzkaller).')
    #for idx, (time_values, coverage_values) in enumerate(zip(coverage_time_data, coverage_coverage_data)):
        #plt.plot(time_values, coverage_values, linestyle='--', color='orange', alpha=0.5,
                #label="Coverage-Guided Coverage" if idx ==0 else None)

    # Calculate and plot average coverage
    #avg_boost_time, avg_boost_coverage = calculate_average_coverage(boost_time_data, boost_coverage_data, max_hours)
    #avg_coverage_time, avg_coverage_coverage = calculate_average_coverage(coverage_time_data, coverage_coverage_data, max_hours)

    #plt.plot(avg_boost_time, avg_boost_coverage, **avg_boost_style)
    #plt.plot(avg_coverage_time, avg_coverage_coverage, **avg_coverage_style)
    
    # Display crash counts as text instead of in the legend
    plt.text(0.02, 0.25,f'SyzBoost Crashes:\n'
        f'  SAN: {boost_crash_counts["SAN"]}\n'
        f'  Kernel BUG: {boost_crash_counts["kernel BUG"]}\n'
        f'  BUG: {boost_crash_counts["BUG"]}\n'
        f'  WARNING: {boost_crash_counts["WARNING"]}\n'
        f'  GPF: {boost_crash_counts["general protection fault"]}',
        fontsize=10, color='blue', transform=plt.gca().transAxes, verticalalignment='bottom', horizontalalignment='left')
    
    plt.text(0.02, 0.02,
        f'Syzkaller Crashes:\n'
        f'  SAN: {coverage_crash_counts["SAN"]}\n'
        f'  Kernel BUG: {coverage_crash_counts["kernel BUG"]}\n'
        f'  BUG: {coverage_crash_counts["BUG"]}\n'
        f'  WARNING: {coverage_crash_counts["WARNING"]}\n'
        f'  GPF: {coverage_crash_counts["general protection fault"]}',
        fontsize=10, color='orange', transform=plt.gca().transAxes, verticalalignment='bottom', horizontalalignment='left')

    ''''
    # Update legend with crash counts
    labels = [
        f'Boost Crashes - SAN: {boost_crash_counts["SAN"]}, '
        f'Kernel BUG: {boost_crash_counts["kernel BUG"]}, '
        f'BUG: {boost_crash_counts["BUG"]}, '
        f'WARNING: {boost_crash_counts["WARNING"]}, '
        f'GPF: {boost_crash_counts["general protection fault"]}',

        f'Coverage Crashes - SAN: {coverage_crash_counts["SAN"]}, '
        f'Kernel BUG: {coverage_crash_counts["kernel BUG"]}, '
        f'BUG: {coverage_crash_counts["BUG"]}, '
        f'WARNING: {coverage_crash_counts["WARNING"]}, '
        f'GPF: {coverage_crash_counts["general protection fault"]}'
    ]
'''

    # Plot hitmap_time as vertical lines for each log
    #for hitmap_delta in boost_hitmap_times:
    #    if hitmap_delta is not None and hitmap_delta <= max_hours:
    #        plt.axvline(x=hitmap_delta, color='blue', linestyle=':', linewidth=1, label='Boost Hitmap Time')

    #for hitmap_delta in coverage_hitmap_times:
    #    if hitmap_delta is not None and hitmap_delta <= max_hours:
    #        plt.axvline(x=hitmap_delta, color='orange', linestyle=':', linewidth=1, label='Coverage Hitmap Time')


    # Add title, labels, and legend
    plt.title('Coverage Values with Hitmap and Crash Events')
    plt.xlabel('Time (hours)')
    plt.ylabel('Coverage Value')
    plt.xlim(0, max_hours)
    plt.legend()
    plt.grid(True)

    # Save the figure
    plt.savefig(output_filename)
    plt.close()
    print(f"Figure saved as {output_filename}")

# Main function
def main():
    parser = argparse.ArgumentParser(description='Plot coverage data with multiple boost and coverage logs.')
    parser.add_argument('--boost_logs', nargs='+', required=True, help='List of boost log filenames.')
    parser.add_argument('--coverage_logs', nargs='+', required=True, help='List of coverage-guided log filenames.')
    #parser.add_argument('--boost_crash_logs', nargs='+', help='List of boost crash log filenames (JSON).')
    #parser.add_argument('--coverage_crash_logs', nargs='+', help='List of coverage crash log filenames (JSON).')
    parser.add_argument('--output', required=True, help='Output filename for the figure (e.g., coverage_plot.png).')
    parser.add_argument('--crash_report', required=True, help='Output filename for the crashes during max_hours (e.g., crash_report.json).')
    parser.add_argument('--max_hours', type=float, default=72, help='Max hours to display on x-axis.')

    args = parser.parse_args()

    global_crash_source = {}

    boost_crash_events_global = set()
    coverage_crash_events_global = set()

    boost_coverage_data = []
    boost_time_data = []
    boost_crash_events = []
    boost_hitmap_times = []
    boost_crash_counts = {'kernel BUG': 0, 'BUG': 0, 'SAN': 0, 'WARNING': 0, 'general protection fault': 0}

    coverage_coverage_data = []
    coverage_time_data = []
    coverage_crash_events = []
    coverage_hitmap_times = []
    coverage_crash_counts = {'kernel BUG': 0, 'BUG': 0, 'SAN': 0, 'WARNING': 0, 'general protection fault': 0}

    # Process each boost log file
    for idx, log_filename in enumerate(args.boost_logs):
        time_values, coverage_values, hitmap_time, initial_timestamp = extract_coverage_and_seeds(
                log_filename,
                crash_counts=boost_crash_counts,
                global_crash_events=boost_crash_events_global,
                max_hours=args.max_hours,
                crash_event_sources = global_crash_source,
                is_boost=True
                )
        boost_coverage_data.append(coverage_values)
        boost_time_data.append(time_values)
        boost_hitmap_times.append(hitmap_time)

    # Process each coverage-guided log file
    for i, log_filename in enumerate(args.coverage_logs):
        time_values, coverage_values, hitmap_time, initial_timestamp = extract_coverage_and_seeds(
                log_filename,
                crash_counts=coverage_crash_counts,
                global_crash_events=coverage_crash_events_global,
                max_hours=args.max_hours,
                crash_event_sources = global_crash_source,
                is_boost=False
                )
        coverage_coverage_data.append(coverage_values)
        coverage_time_data.append(time_values)
        coverage_hitmap_times.append(hitmap_time)

    crash_report_data = [
            {
                "crash_hash": crash_hash,
                "message": info["message"],
                "boost_logs": info["boost"],
                "original_logs": info["original"],
                }
            for crash_hash, info in global_crash_source.items()
            ]
    with open(args.crash_report, "w") as json_file:
        json.dump(crash_report_data, json_file, indent=4)

    # Plot the data
    plot_coverage_with_crashes(boost_coverage_data, boost_time_data, boost_hitmap_times,
            coverage_coverage_data, coverage_time_data, coverage_hitmap_times,
            boost_crash_counts, coverage_crash_counts,
            args.output, args.max_hours)

if __name__ == "__main__":
    main()

