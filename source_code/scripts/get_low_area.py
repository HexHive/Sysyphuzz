import json
import argparse
import os
import numpy as np


def parse_json_and_filter(input_file, percentage):
    """
    Parse JSON file, construct lists of BB addresses and CoverNumbers, 
    and filter based on the provided percentage.

    Args:
        input_file (str): Path to the JSON file.
        percentage (float): Percentage to filter the data.

    Returns:
        dict: Filtered data with statistics and related information.
    """
    bb_address_list = []
    coverNumber_list = []

    try:
        with open(input_file, 'r') as file:
            data = json.load(file)

        # Handle different JSON formats
        if isinstance(data, list):  # Format 1
            entries = data
        elif isinstance(data, dict) and "SelectedBBs" in data:  # Format 2
            entries = data["SelectedBBs"]
        else:
            raise ValueError("Unsupported JSON format")

        # Construct lists
        for entry in entries:
            cover_number = entry.get("CoverNumber", 0)
            bb_addresses = entry.get("BBAddressList", [])
            bb_address_list.extend(bb_addresses)
            coverNumber_list.extend([cover_number] * len(bb_addresses))

        # Calculate the number of entries to keep based on the percentage
        total_blocks = len(bb_address_list)
        highlight_blocks = max(1, int(total_blocks * percentage / 100))

        # Determine the last index to keep
        chosen_cover_hit = coverNumber_list[highlight_blocks - 1]
        index = highlight_blocks - 2
        while index >= 0 and coverNumber_list[index] == chosen_cover_hit:
            index -= 1

        # Final target blocks to keep
        targetpcs = bb_address_list[:index + 1]
        filtered_cover_numbers = coverNumber_list[:index + 1]

        # Calculate statistics for the filtered coverNumber_list
        median_cover_number = np.median(filtered_cover_numbers)
        min_cover_number = min(filtered_cover_numbers)
        max_cover_number = max(filtered_cover_numbers)
        avg_cover_number = np.mean(filtered_cover_numbers)

        # Return filtered data with statistics
        return {
            "FilteredBBAddressList": targetpcs,
            "FilteredCoverNumberList": filtered_cover_numbers,
            "TotalBlocks": total_blocks,
            "MedianCoverNumber": median_cover_number,
            "MinCoverNumber": min_cover_number,
            "MaxCoverNumber": max_cover_number,
            "AvgCoverNumber": avg_cover_number
        }

    except FileNotFoundError:
        print(f"File not found: {input_file}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file: {input_file}")
        return None
    except ValueError as e:
        print(e)
        return None


def process_multiple_files(input_files, percentage, output_dir):
    """
    Process multiple JSON files and save filtered data for each file.

    Args:
        input_files (list of str): List of input JSON file paths.
        percentage (float): Percentage to filter the data.
        output_dir (str): Directory to save the filtered JSON files.
    """
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    for idx, input_file in enumerate(input_files,start=1):
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_dir, f"filtered_{filename}_{idx}")

        filtered_data = parse_json_and_filter(input_file, percentage)
        if filtered_data:
            # Save the filtered data
            with open(output_file, 'w') as outfile:
                json.dump(filtered_data, outfile, indent=4)
            results[f"{filename}_{idx}"] = filtered_data
            print(f"Processed and saved filtered data for {filename} to {output_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Process multiple JSON files and filter BB addresses by percentage.")
    parser.add_argument("--input_files", nargs='+', required=True, help="Paths to the input JSON files.")
    parser.add_argument("--per", type=float, required=True, help="Percentage to filter the BB addresses.")
    parser.add_argument("--output_dir", required=True, help="Directory to save the filtered JSON files.")

    args = parser.parse_args()

    # Process multiple files
    results = process_multiple_files(args.input_files, args.per, args.output_dir)

    # Print summary
    if results:
        print("\nSummary of processed files:")
        for filename, data in results.items():
            print(f"File: {filename}")
            print(f"  Total Blocks: {data['TotalBlocks']}")
            print(f"  Filtered BB Count: {len(data['FilteredBBAddressList'])}")
            print(f"  Median CoverNumber: {data['MedianCoverNumber']}")
            print(f"  Min CoverNumber: {data['MinCoverNumber']}")
            print(f"  Max CoverNumber: {data['MaxCoverNumber']}")
            print(f"  Avg CoverNumber: {data['AvgCoverNumber']:.2f}")


if __name__ == "__main__":
    main()

