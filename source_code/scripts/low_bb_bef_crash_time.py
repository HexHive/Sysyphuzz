import os
import re
import json
import csv
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_timestamps(log_path, crash_time):
    pattern = re.compile(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*No candidate&canTriage jobs and smashQueue is empty")
    timestamps = []
    with open(log_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                time_str = match.group(1)
                ts = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                if ts <= crash_time:
                    timestamps.append(ts)
    return sorted(timestamps)

def find_bb_json(base_dir, ts):
    subdir = ts.strftime("%Y%m%d_%H")
    bb_dir = Path(base_dir) / subdir
    if not bb_dir.exists():
        return None
    target_file = f"UnderCoveredBBs_{ts.strftime('%H%M')}.json"
    file_path = bb_dir / target_file
    if file_path.exists():
        return file_path
    # Try previous minute if exact file not found
    prev_ts = ts - timedelta(minutes=1)
    fallback_file = f"UnderCoveredBBs_{prev_ts.strftime('%H%M')}.json"
    fallback_path = bb_dir / fallback_file
    return fallback_path if fallback_path.exists() else None

def collect_bb_addresses(bb_json_paths):
    bb_set = set()
    for path in bb_json_paths:
        with open(path, 'r') as f:
            data = json.load(f)
            bb_set.update(data.get("BBSet", []))
    return sorted(bb_set)

def map_single_address(addr, vmlinux_path):
    try:
        cmd = ["addr2line", "-e", vmlinux_path, "-f", "-C", addr]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        lines = output.split("\n")
        if len(lines) >= 2:
            return addr, f"{lines[0]} @ {lines[1]}"
        else:
            return addr, output
    except subprocess.CalledProcessError:
        return addr, "Unknown"
    except Exception as e:
        return addr, f"Error: {str(e)}"

def map_bb_addresses(bb_set, vmlinux_path, max_workers=8):
    addr_to_source = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_addr = {
            executor.submit(map_single_address, addr, vmlinux_path): addr for addr in bb_set
        }
        for future in as_completed(future_to_addr):
            addr, result = future.result()
            addr_to_source[addr] = result
    return addr_to_source

def save_bb_csv(output_path, bb_list):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["BB_Address"])
        for bb in bb_list:
            writer.writerow([bb])

def save_ubb_csv(output_path, mapped):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["BB_Address", "Source_Location"])
        for addr, source in mapped.items():
            writer.writerow([addr, source])

def main():
    parser = argparse.ArgumentParser(description="Process syzkaller log and extract low-frequency BBs before a crash.")
    parser.add_argument("-syzlog", required=True, help="Path to syzkaller running log")
    parser.add_argument("-bblog", required=True, help="Base directory for BB frequency logs")
    parser.add_argument("-vmlinux", required=True, help="Path to vmlinux for addr2line")
    parser.add_argument("-time_stamp", required=True, help="Crash time in format YYYY/MM/DD HH:MM:SS")
    parser.add_argument("-o", required=True, help="Output base directory")
    args = parser.parse_args()

    crash_time = datetime.strptime(args.time_stamp, "%Y/%m/%d %H:%M:%S")
    timestamps = extract_timestamps(args.syzlog, crash_time)

    csv_dir = Path(args.o)
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "LBB_timepoint.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp"])
        for ts in timestamps:
            writer.writerow([ts.strftime("%Y/%m/%d %H:%M:%S")])

    json_paths = []
    for ts in timestamps:
        path = find_bb_json(args.bblog, ts)
        if path:
            json_paths.append(path)

    bb_set = collect_bb_addresses(json_paths)
    bb_csv_path = csv_dir / f"low_frequency_bb_{crash_time.strftime('%Y_%m_%d_%H_%M_%S')}.csv"
    save_bb_csv(bb_csv_path, bb_set)

    mapped = map_bb_addresses(bb_set, args.vmlinux)
    ubb_path = csv_dir / f"UBB_{crash_time.strftime('%Y_%m_%d_%H_%M_%S')}.csv"
    save_ubb_csv(ubb_path, mapped)

if __name__ == "__main__":
    main()
