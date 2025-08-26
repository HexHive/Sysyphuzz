import argparse
import re
import csv

def parse_args():
    parser = argparse.ArgumentParser(description='Overlap analysis between crash trace and low-frequency BB CSV files.')
    parser.add_argument('-crash_csv', required=True, help='Path to the crash trace CSV file')
    parser.add_argument('-lf_csv', required=True, help='Path to the low-frequency area CSV file')
    parser.add_argument('-o', required=False, default='overlap_result.csv', help='Output CSV file for overlap result')
    return parser.parse_args()

def remove_offset(func):
    return re.sub(r'\+0x[0-9a-fA-F]+/0x[0-9a-fA-F]+', '', func).strip()

def load_crash_csv(path):
    data = []
    pattern = re.compile(r'(\S+)\s+(.+:\d+)')
    with open(path, 'r') as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            match = pattern.match(line)
            if not match:
                print(f"Warning: Skipping malformed line {idx} in '{path}': {line}")
                continue
            func, source = match.groups()
            data.append([func.strip(), source.strip()])
    return data

def load_csv(path):
    data = []
    with open(path, 'r') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader, 1):
            if len(row) != 2:
                print(f"Warning: Skipping malformed line {idx} in '{path}': {row}")
                continue
            data.append(row)
    return data

def analyze_overlap(crash_items, lf_items):
    total_overlap = []
    middle_overlap = []
    low_overlap = []

    for crash_func, crash_source in crash_items:
        crash_func_clean = remove_offset(crash_func)
        crash_src_file, _, crash_line = crash_source.partition(':')

        for bb_addr, bb_source in lf_items:
            bb_func, _, bb_location = bb_source.partition('@')
            bb_func = bb_func.strip()
            bb_location = bb_location.strip()

            # Extract source file starting from 'linux/'
            linux_idx = bb_location.find('linux/')
            if linux_idx != -1:
                bb_location = bb_location[linux_idx + len('linux/'):]
            
            bb_src_file, _, bb_line = bb_location.partition(':')

            if (crash_func_clean == bb_func and 
                crash_src_file == bb_src_file and 
                crash_line == bb_line):
                total_overlap.append((crash_func, crash_source, bb_addr, bb_func, bb_location))

            elif crash_func_clean == bb_func and crash_src_file == bb_src_file:
                middle_overlap.append((crash_func, crash_source, bb_addr, bb_func, bb_location))

            elif crash_src_file == bb_src_file:
                low_overlap.append((crash_func, crash_source, bb_addr, bb_func, bb_location))

    return total_overlap, middle_overlap, low_overlap

def save_results(output_path, total, middle, low):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Overlap_Level', 'Crash_Func', 'Crash_Source', 'BB_Address', 'BB_Source'])

        for entry in total:
            writer.writerow(['Total'] + list(entry))

        for entry in middle:
            writer.writerow(['Middle'] + list(entry))

        for entry in low:
            writer.writerow(['Low'] + list(entry))

    print(f'Overlap results saved in: {output_path}')
    print(f'Total overlaps: {len(total)}')
    print(f'Middle overlaps: {len(middle)}')
    print(f'Low overlaps: {len(low)}')

def main():
    args = parse_args()

    crash_items = load_crash_csv(args.crash_csv)
    lf_items = load_csv(args.lf_csv)

    total, middle, low = analyze_overlap(crash_items, lf_items)

    save_results(args.o, total, middle, low)

if __name__ == '__main__':
    main()
