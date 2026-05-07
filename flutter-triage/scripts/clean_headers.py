import os
import sys
import re

def clean_file(file_path):
    print(f"Cleaning {file_path}...")
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find the first occurrence of '{' or '['
    match = re.search(r'[\[{]', content)
    if not match:
        print(f"No JSON start found in {file_path}")
        return
    
    json_start = match.start()
    clean_content = content[json_start:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(clean_content)
    print(f"Cleaned {file_path}")

def clean_dir(directory):
    for filename in os.listdir(directory):
        if filename.startswith('page_') and filename.endswith('.json'):
            clean_file(os.path.join(directory, filename))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clean_headers.py <directory>")
        sys.exit(1)
    clean_dir(sys.argv[1])
