import os
import json
import argparse

def classify_crashes(input_json, output_dir):
    with open(input_json, 'r') as f:
        data = json.load(f)

    categories = {
        "sanitizer": {"filter": lambda msg: "SAN" in msg, "entries": []},
        "bug": {"filter": lambda msg: "BUG:" in msg or "kernel BUG" in msg, "entries": []},
        "gpe": {"filter": lambda msg: "general protection fault" in msg, "entries": []}
    }

    for entry in data:
        message = entry.get("message", "")
        for key, cat in categories.items():
            if cat["filter"](message):
                cat["entries"].append(entry)
                break

    os.makedirs(output_dir, exist_ok=True)

    for key, cat in categories.items():
        entries = cat["entries"]
        only_boost = [e for e in entries if e["boost_logs"] and not e["original_logs"]]
        only_original = [e for e in entries if not e["boost_logs"] and e["original_logs"]]
        both_present = [e for e in entries if e["boost_logs"] and e["original_logs"]]

        result = {
            "only_boost_count": len(only_boost),
            "only_original_count": len(only_original),
            "both_present_count": len(both_present),
            "only_boost": only_boost,
            "only_original": only_original,
            "both_present": both_present
        }

        output_path = os.path.join(output_dir, f"{key}.json")
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=4)

    print(f"Classification complete. Output saved to: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify crash logs into categories.")
    parser.add_argument('--input_json', required=True, help='Path to input JSON file')
    parser.add_argument('--output_dir', required=True, help='Directory to store output JSON files')
    args = parser.parse_args()

    classify_crashes(args.input_json, args.output_dir)

