"""
Prints all mod directory sorted by code file size to determine the size of a mod.
"""
import os

def format_size(bytes_val):
    # Formats a byte value to the largest unit
    if bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} KB"
    else:
        return f"{bytes_val} bytes"

main_path = '/Users/henning/Lokal/GitHub'
result = []

for entry in os.listdir(main_path):
    full_entry_path = os.path.join(main_path, entry)
    if os.path.isdir(full_entry_path):
        target_path = os.path.join(full_entry_path, '1.21.8')
        if os.path.isdir(target_path):
            total_size = 0
            for dirpath, _, filenames in os.walk(target_path):
                for filename in filenames:
                    if filename.endswith('.java'):
                        full_path = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(full_path)
                        except Exception as e:
                            print(f"Error reading {full_path}: {e}")
            result.append((entry, total_size))

# Sort by descending size and print
if result:
    for path, size in sorted(result, key=lambda x: x[1], reverse=True):
        print(f"{path}: {format_size(size)}")
else:
    print("No 1.21.8 directories with .java files found.")
