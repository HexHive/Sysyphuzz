import json
import argparse
import os
import numpy as np


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


def calculate_overlap_with_stats(selected_bbs, targetpcs, target_cover_numbers):
    """
    Calculate the overlap and compute CoverNumber statistics for the overlapping BBs.

    Args:
        selected_bbs (list): List of BB addresses from the first file.
        targetpcs (list): List of BB addresses from the current file.
        target_cover_numbers (list): List of CoverNumber values corresponding to the targetpcs.

    Returns:
        dict: Overlap percentage and statistics for the overlapping CoverNumbers.
    """
    selected_set = set(selected_bbs)
    target_set = set(targetpcs)
    overlap = selected_set.intersection(target_set)

    # Map BB addresses to their CoverNumber
    target_bb_to_cover = dict(zip(targetpcs, target_cover_numbers))

    # Get CoverNumber values for overlapping BBs
    overlapping_cover_numbers = [target_bb_to_cover[bb] for bb in overlap if bb in target_bb_to_cover]

    if overlapping_cover_numbers:
        stats = {
            "OverlapPercentage": (len(overlap) / len(selected_set)) * 100 if selected_set else 0,
            "MinCoverNumber": min(overlapping_cover_numbers),
            "MedianCoverNumber": np.median(overlapping_cover_numbers),
            "AvgCoverNumber": np.mean(overlapping_cover_numbers),
            "MaxCoverNumber": max(overlapping_cover_numbers),
        }
    else:
        stats = {
            "OverlapPercentage": 0,
            "MinCoverNumber": None,
            "MedianCoverNumber": None,
            "AvgCoverNumber": None,
            "MaxCoverNumber": None,
        }

    return stats


def process_files(input_files, output_file):
    """
    Process multiple JSON files and calculate overlap percentages and CoverNumber stats.

    Args:
        input_files (list): List of input JSON files.
        output_file (str): Output file to save results.
    """
    if len(input_files) < 2:
        print("At least two input files are required.")
        return

    # Load the first file and extract selected_bbs
    first_file_data = load_json_file(input_files[0])
    if not first_file_data or "FilteredBBAddressList" not in first_file_data:
        print(f"Invalid or missing data in the first file: {input_files[0]}")
        return

    selected_bbs = first_file_data["FilteredBBAddressList"]

    # Prepare results
    results = {"SelectedBBs": selected_bbs, "FileOverlapStats": {}}

    # Process subsequent files
    for input_file in input_files[1:]:
        file_data = load_json_file(input_file)
        if not file_data or "FilteredBBAddressList" not in file_data or "FilteredCoverNumberList" not in file_data:
            print(f"Invalid or missing data in file: {input_file}")
            continue

        targetpcs = file_data["FilteredBBAddressList"]
        target_cover_numbers = file_data["FilteredCoverNumberList"]

        overlap_stats = calculate_overlap_with_stats(selected_bbs, targetpcs, target_cover_numbers)
        results["FileOverlapStats"][os.path.basename(input_file)] = overlap_stats

    # Save results to the output file
    with open(output_file, 'w') as outfile:
        json.dump(results, outfile, indent=4)
    print(f"Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Calculate overlap percentages and CoverNumber stats across JSON files.")
    parser.add_argument("--input_files", nargs='+', required=True, help="List of input JSON files.")
    parser.add_argument("--output_file", required=True, help="Output file to save results.")
    args = parser.parse_args()

    # Process the input files and calculate overlap stats
    process_files(args.input_files, args.output_file)


if __name__ == "__main__":
    main()

