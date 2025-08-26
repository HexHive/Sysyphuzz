import argparse
import re
import csv

COMMON_PATTERNS = [
    r'do_syscall_64',
    r'do_syscall_x64',
    r'entry_SYSCALL_64',
    r'entry_SYSCALL_64_after_hwframe',
    r'lib/dump_stack\.c',
    r'kasan_report',
    r'resume_user_mode',
    r'exit_to_user_mode',
    r'exit_to_user_mode_loop',
    r'report\.c',
    r'common\.c',
    r'^RIP:', r'^Code:', r'^RSP:', r'^EFLAGS:', r'^ORIG_RAX:',
    r'^RAX:', r'^RBX:', r'^RCX:', r'^RDX:', r'^RSI:', r'^RDI:',
    r'^RBP:', r'^R08:', r'^R09:', r'^R10:', r'^R11:', r'^R12:',
    r'^R13:', r'^R14:', r'^R15:',
    r'^page:', r'^head:', r'^raw:',
    r'^The buggy address belongs to',
    r'^Memory state around the buggy address:',
    r'^which belongs to the cache',
    r'^The buggy address is located',
    r'^page last allocated via',
    r'^page last free pid',
    r'^page_owner',
    r'^page dumped because'
]

def is_common_line(line):
    return any(re.search(pattern, line) for pattern in COMMON_PATTERNS)

def extract_trace_lines(lines, start_marker, end_marker):
    in_section = False
    extracted = []

    for line in lines:
        line = line.strip()
        if start_marker in line:
            in_section = True
            continue
        if in_section:
            if line == "" or end_marker in line:
                break
            if is_common_line(line):
                continue

            match = re.search(r'([a-zA-Z0-9_+.]+(?:\+0x[0-9a-f]+)?(?:/\S+)?)\s+(.*:\d+)', line)
            if match:
                extracted.append((match.group(1), match.group(2)))
            else:
                fallback = re.search(r'([a-zA-Z0-9_+.]+(?:\+0x[0-9a-f]+)?)', line)
                if fallback:
                    extracted.append((fallback.group(1), ''))
    return extracted

def extract_all_traces(input_path, output_csv):
    with open(input_path, 'r', encoding='latin1') as f:
        lines = f.readlines()

    all_results = []
    all_results += extract_trace_lines(lines, '<TASK>', '</TASK>')
    all_results += extract_trace_lines(lines, 'Allocated by task', 'Freed by task')
    all_results += extract_trace_lines(lines, 'Freed by task', 'The buggy address belongs to')
    all_results += extract_trace_lines(lines, 'Last potentially related work creation', 'The buggy address belongs to')
    all_results += extract_trace_lines(lines, 'page last allocated via', 'page last free pid')
    all_results += extract_trace_lines(lines, 'page last free pid', 'Memory state around')

    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for func, loc in all_results:
            if loc:
                writer.writerow([f'{func} {loc}'])
            else:
                writer.writerow([func])

def main():
    parser = argparse.ArgumentParser(description="Extract call trace and alloc stack to CSV")
    parser.add_argument('-i', '--input', required=True, help='Path to crash report')
    parser.add_argument('-o', '--output', default='clean_trace.csv', help='Output CSV file')
    args = parser.parse_args()
    extract_all_traces(args.input, args.output)

if __name__ == "__main__":
    main()
