#!/usr/bin/env python3

# Take 1st arg. as location to create a multicluster entry list.
# 1 cluster = 4096 B; 1 entry = 32 B; so 1 cluster holds 128 entries.

import random
import sys

from pathlib import Path

def create_filenames(parent, count=140):
    file_paths = []
    for i in range(count):
        name = f"file {i+1} of {count} - 34 chars or more.txt"
        file_paths.append(Path(parent) / name)
    return file_paths

def create_files_in_random_order(paths):
    random.shuffle(paths)
    for p in path:
        p.touch()


def main():
    parent_dir = Path(sys.argv[1]).resolve()
    if not parent_dir.is_dir():
        print(f"ERROR: {parent_dir} doesn't exist.")
        exit(1)

    file_paths = create_filenames(parent_dir)
    create_files_in_random_order(file_paths)


if __name__ == '__main__':
    main()
