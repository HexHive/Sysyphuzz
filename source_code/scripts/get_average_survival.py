import json
import argparse
import numpy as np
from collections import defaultdict


def load_json_file(file_path):
    """
    Load JSON data from a file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: JSON data as a dictionary.
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return None


def extract_overlap_stats(data):
    """
    Extract FileOverlapStats from the JSON data.

    Args:
        data (dict): JSON data.

    Returns:
        dict: FileOverlapStats dictionary or None if not present.
    """
    return data.get("FileOverlapStats", {})


def calculate_average_overlap_stats(all_stats, file_names):
    """
    Calculate the average values for metrics in FileOverlapStats based on index.

    Args:
        all_stats (list): List of FileOverlapStats dictionaries from multiple JSON files.
        file_names (list): List of input file names for labeling.

    Returns:
        dict: Dictionary containing the combined averages for each index.
    """
    combined_stats = defaultdict(lambda: defaultdict(list))

    # Aggregate metrics based on the index in FileOverlapStats
    for file_stats, file_name in zip(all_stats, file_names):
        for idx, (entry_name, metrics) in enumerate(file_stats.items()):
            combined_stats[idx]["files"].append(entry_name)
            for metric, value in metrics.items():
                combined_stats[idx][metric].append(value)

    # Calculate averages for each index
    average_stats = {}
    for idx, stats in combined_stats.items():
        files_combined = ",".join(stats["files"])
        average_metrics = {
            metric: np.mean(values) for metric, values in stats.items() if metric != "files"
        }
        average_stats[files_combined] = average_metrics

    return average_stats


def process_files(input_files, output_file):
    """
    Process multiple JSON files, extract FileOverlapStats, and calculate average metrics.

    Args:
        input_files (list): List of input JSON files.
        output_file (str): Output file to save results.
    """
    all_stats = []
    file_names = []

    # Extract FileOverlapStats from each file
    for input_file in input_files:
        data = load_json_file(input_file)
        if data:
            file_overlap_stats = extract_overlap_stats(data)
            if file_overlap_stats:
                all_stats.append(file_overlap_stats)
                file_names.append(input_file)

    if not all_stats:
        print("No valid FileOverlapStats found in the input files.")
        return

    # Calculate average overlap stats
    average_stats = calculate_average_overlap_stats(all_stats, file_names)

    # Save results to the output file
    with open(output_file, 'w') as outfile:
        json.dump(average_stats, outfile, indent=4)
    print(f"Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Calculate average FileOverlapStats from multiple JSON files.")
    parser.add_argument("--input_files", nargs='+', required=True, help="List of input JSON files.")
    parser.add_argument("--output_file", required=True, help="Output file to save the results.")
    args = parser.parse_args()

    # Process files and calculate average overlap stats
    process_files(args.input_files, args.output_file)


if __name__ == "__main__":
    main()

