import json
import os
import sys

def combine_json_files(input_dir, output_file):
    all_items = []
    page_files = sorted([f for f in os.listdir(input_dir) if f.startswith('page_') and f.endswith('.json')])

    for page_file in page_files:
        with open(os.path.join(input_dir, page_file), 'r') as f:
            try:
                data = json.load(f)
                all_items.extend(data.get('items', []))
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {page_file}", file=sys.stderr)

    combined_data = {
        "total_count": len(all_items),
        "incomplete_results": False,
        "items": all_items
    }

    with open(output_file, 'w') as f:
        json.dump(combined_data, f, indent=2)

    print(f"Combined {len(all_items)} items from {len(page_files)} pages into {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python combine_json.py <input_directory> <output_file>", file=sys.stderr)
        sys.exit(1)

    input_dir = sys.argv[1]
    output_file = sys.argv[2]
    combine_json_files(input_dir, output_file)
