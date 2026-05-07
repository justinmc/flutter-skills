import json
import sys

def main():
    if len(sys.argv) < 4 or len(sys.argv) % 2 != 0:
        print("Usage: python combine_all.py <output_file> <list_name_1> <json_file_1> [<list_name_2> <json_file_2> ...]", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]
    combined_data = {}

    for i in range(2, len(sys.argv), 2):
        list_name = sys.argv[i]
        json_file = sys.argv[i+1]
        try:
            with open(json_file, 'r') as f:
                combined_data[list_name] = json.load(f)
        except FileNotFoundError:
            print(f"Warning: File not found: {json_file}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {json_file}", file=sys.stderr)

    with open(output_file, 'w') as f:
        json.dump(combined_data, f, indent=2)

    print(f"Combined {len(combined_data)} lists into {output_file}")

if __name__ == "__main__":
    main()
