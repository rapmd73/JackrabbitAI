# Section 1 - Non-Technical Description

This program looks through a folder of image files, finds PNG images whose file paths contain the text "noframe", skips any that are already present in a slideshow folder, copies the remaining ones into the slideshow folder using sequential numeric file names, and prints the path of each image it copies.

# Section 2 - Technical Analysis

The script imports modules for filesystem operations, command-line access, file copying, and hashing. Its execution entry point checks that exactly two command-line arguments are provided: the first is treated as the slideshow (target) directory and the second as the scanning (source) directory. If the argument count is incorrect, it prints a usage message and exits.

file_hash(path, chunk_size=8192)
- Opens the given file in binary mode and reads it in chunks of up to 8192 bytes.
- Updates a SHA-256 hash object with each chunk and returns the final hexadecimal digest string.
- This function produces a content fingerprint for a file.

load_existing_files(slideshow_dir)
- Iterates over entries in the slideshow directory.
- Skips entries that are not regular files.
- For each file, splits its filename into base and extension. If the base is composed only of digits, it interprets that base as an integer and tracks the largest such integer seen as max_number.
- Groups files by their byte size in a dictionary mapping size -> list of file paths.
- Returns the dictionary of existing files keyed by size and the maximum numeric base found among filenames.

is_duplicate(src_path, existing_by_size)
- Gets the byte size of the source file.
- If that size is not present as a key in the existing_by_size mapping, the function returns False (not a duplicate).
- If the size matches one or more existing files, it computes the SHA-256 hash of the source file.
- It then computes the SHA-256 hash for each existing file with the same size and compares them to the source hash. If any hash matches, it returns True (duplicate).
- If none match, it returns False.

copy_and_rename(slideshow_dir, scanning_dir)
- Validates that both slideshow_dir and scanning_dir exist as directories; if not, it raises a ValueError.
- Calls load_existing_files to obtain existing_by_size and a counter value (the highest numeric base found in existing filenames). It then increments counter by 1 so new files will start after the highest existing numeric name.
- Walks the scanning_dir tree using os.walk, and for each file encountered (files are processed in sorted order):
  - Builds the full source path.
  - Continues (skips) unless the source path contains the substring "noframe" and the filename ends with ".png".
  - Skips the entry if the source path is not a regular file.
  - Calls is_duplicate with the source path and existing_by_size; if it returns True, the file is skipped.
  - If not a duplicate, the script prints the source path to standard output.
  - Determines the filename extension of the source file and constructs a destination filename by concatenating the current counter value and that extension (e.g., "5.png").
  - Copies the source file to the slideshow directory using shutil.copy2 (which preserves metadata where possible).
  - After copying, it gets the size of the newly copied file and adds the destination path to existing_by_size under that size key.
  - Increments the counter so the next copied file gets the next numeric name.

Overall behavior when run as a script
- When invoked with two directory paths, the script scans the source directory tree for PNG files whose paths include "noframe", filters out files that match existing files in the target by comparing file sizes and, when sizes match, SHA-256 hashes, and copies non-duplicate files into the target directory using sequential numeric filenames while printing each copied source path.
