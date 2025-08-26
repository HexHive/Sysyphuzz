import json
import argparse
from statistics import mean


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


def calculate_averages(files):
    """
    Calculate the average values of specified fields across multiple JSON files.

    Args:
        files (list): List of file paths.

    Returns:
        dict: Dictionary with average values for each metric.
    """
    metrics = {
        "MedianCoverNumber": [],
        "MinCoverNumber": [],
        "MaxCoverNumber": [],
        "AvgCoverNumber": []
    }

    # Aggregate values from all files
    for file_path in files:
        data = load_json_file(file_path)
        if data:
            metrics["MedianCoverNumber"].append(data.get("MedianCoverNumber", 0))
            metrics["MinCoverNumber"].append(data.get("MinCoverNumber", 0))
            metrics["MaxCoverNumber"].append(data.get("MaxCoverNumber", 0))
            metrics["AvgCoverNumber"].append(data.get("AvgCoverNumber", 0))

    # Calculate the averages
    averages = {
        metric: mean(values) for metric, values in metrics.items() if values
    }

    return averages


def main():
    parser = argparse.ArgumentParser(description="Calculate average values of specific metrics from multiple JSON files.")
    parser.add_argument("--input_files", nargs='+', required=True, help="List of input JSON files.")
    parser.add_argument("--output_file", required=True, help="Output file to save the averages.")
    args = parser.parse_args()

    # Calculate averages
    averages = calculate_averages(args.input_files)

    # Save results to the output file
    with open(args.output_file, 'w') as outfile:
        json.dump(averages, outfile, indent=4)
    print(f"Results saved to {args.output_file}")


if __name__ == "__main__":
    main()

