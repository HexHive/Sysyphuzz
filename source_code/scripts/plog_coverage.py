import re
import matplotlib.pyplot as plt
from datetime import datetime
import json
import argparse
import numpy as np

# === Global Matplotlib Settings ===
plt.rcParams.update({
    'mathtext.default': 'regular',
    'font.size': 24,
    'pdf.fonttype': 42,
    #'axes.labelweight': 'bold',
    #'font.weight': 'bold'
})

def extract_coverage_and_seeds(filename):
    coverage_values = []
    time_values = []
    hitmap_time = None
    initial_timestamp = None

    with open(filename, 'r') as file:
        for line in file:
            if not hitmap_time and "Begin to analyze Hit Map" in line:
                timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    hitmap_time = datetime.strptime(timestamp_match.group(1), '%Y/%m/%d %H:%M:%S')

            coverage_match = re.search(r'coverage=(\d+)', line)
            if coverage_match:
                timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    current_timestamp = datetime.strptime(timestamp_match.group(1), '%Y/%m/%d %H:%M:%S')
                    if not initial_timestamp:
                        initial_timestamp = current_timestamp
                    time_values.append(current_timestamp)
                    coverage_values.append(int(coverage_match.group(1)))

    # Align times to the "Begin to analyze Hit Map" as t0
    if hitmap_time is None:
        print(f"[Warning] No hitmap time found in {filename}. Skipping this file.")
        return [], []

    time_deltas = [(t - hitmap_time).total_seconds() / 3600 for t in time_values if t >= hitmap_time]
    coverage_values = [c for t, c in zip(time_values, coverage_values) if t >= hitmap_time]

    return time_deltas, coverage_values

def calculate_bounds(time_data, coverage_data, max_hours):
    max_steps = int(max_hours * 10)
    interval = max_hours / max_steps
    coverage_values = np.full((max_steps, len(time_data)), np.nan)

    for run_idx, (times, coverages) in enumerate(zip(time_data, coverage_data)):
        for t, c in zip(times, coverages):
            if 0 <= t <= max_hours:
                index = min(int(t / interval), max_steps - 1)
                coverage_values[index, run_idx] = c

    min_cov = np.nanmin(coverage_values, axis=1)
    max_cov = np.nanmax(coverage_values, axis=1)
    avg_cov = np.nanmean(coverage_values, axis=1)
    avg_time = [i * interval for i in range(max_steps)]

    return avg_time, min_cov, max_cov, avg_cov

def plot_coverage(boost_time_data, boost_coverage_data,
                  cov_time_data, cov_coverage_data,
                  output_file, max_hours):

    avg_time_b, min_b, max_b, avg_b = calculate_bounds(boost_time_data, boost_coverage_data, max_hours)
    avg_time_c, min_c, max_c, avg_c = calculate_bounds(cov_time_data, cov_coverage_data, max_hours)

    plt.figure(figsize=(12, 6))

    # Plot average
    plt.plot(avg_time_b, avg_b, color='red', linestyle='-', linewidth=2, label="Sysyphuzz Avg Coverage")
    plt.plot(avg_time_c, avg_c, color='blue', linestyle='-', linewidth=2, label="Syzkaller Avg Coverage")

    # Shaded regions
    plt.fill_between(avg_time_b, min_b, max_b, color='red', alpha=0.15, label="Sysyphuzz Coverage Range")
    plt.fill_between(avg_time_c, min_c, max_c, color='blue', alpha=0.15, label="Syzkaller Coverage Range")
    import matplotlib.ticker as ticker
    ax = plt.gca()
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{int(x/1000)}'))
    # Labels and style
    plt.xlabel("Time (hours)")
    plt.ylabel("Coverage Value (K)")
    #plt.title("Coverage Over Time Aligned by Corpus Replay Finished Time (t0)")
    plt.xlim(0, max_hours)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, format='pdf', dpi=300)
    plt.close()
    print(f"✅ Plot saved to {output_file}")
    # ==== Final Avg Coverage Difference ====
    final_boost = avg_b[-1]
    final_cov = avg_c[-1]
    diff = final_boost - final_cov
    print(f"📊 Final Avg Coverage SyzBoost = {final_boost:.2f}")
    print(f"📊 Final Avg Coverage Diff (SyzBoost - Syzkaller) = {diff:.2f}")
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--boost_logs', nargs='+', required=True, help='Boost logs')
    parser.add_argument('--coverage_logs', nargs='+', required=True, help='Coverage-guided logs')
    parser.add_argument('--output', required=True, help='Output PDF file')
    parser.add_argument('--max_hours', type=float, default=72, help='Maximum hour to plot')
    args = parser.parse_args()

    boost_time_data = []
    boost_coverage_data = []
    for log in args.boost_logs:
        t, c = extract_coverage_and_seeds(log)
        if t and c:
            boost_time_data.append(t)
            boost_coverage_data.append(c)

    cov_time_data = []
    cov_coverage_data = []
    for log in args.coverage_logs:
        t, c = extract_coverage_and_seeds(log)
        if t and c:
            cov_time_data.append(t)
            cov_coverage_data.append(c)

    plot_coverage(boost_time_data, boost_coverage_data,
                  cov_time_data, cov_coverage_data,
                  args.output, args.max_hours)

if __name__ == "__main__":
    main()






