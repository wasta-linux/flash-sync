#!/usr/bin/env python3

# Correctly update flash memory (FAT) contents for simple music players.
# Take 2 inputs:
#   - source folder
#   - destination device
#
# Requires:
#   - fatsort (pyfilesystem2, pyfatfs)
#   - pkexec
#   - zenity
#
# References:
#   https://www.pjrc.com/tech/8051/ide/fat32.html
#   https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system

import argparse

from pprint import pprint

from disk import Disk
from util import sort_dir_groups


def show_directories(disk):
    for p in disk.partitions.values():
        dir_groups = p.get_dir_list(disk.fat_device)
        pprint(dir_groups)

def sort_files(disk, verbose=False):
    for p in disk.partitions.values():
        dir_groups = p.get_dir_list(disk.fat_device)
        sorted_dir_groups = sort_dir_groups(disk.fat_device, dir_groups, verbose)
        for g in sorted_dir_groups.values():
            chain = g.get('chain')
            entries = []
            # for fdict in g.get('files'):
            #     elist = list(fdict.values())[0]
            #     for e in elist:
            #         entries.append(e)
            for flist in g.get('files'):
                entries.extend(flist[1])
            if len(entries) > 0:
                p.set_cluster_chain_entries(disk.fat_device, chain, entries)

def list_files(disk, filter=None):
    for p in disk.partitions.values():
        for f in p.files:
            if not filter or f.type == filter:
                print(f.get_full_path())

def show_info(disk):
    print(f"Device: {disk.fat_device.path}")
    print(f"\nMBR:")
    print(f"  {disk.mbr.end_signature = }")
    print(f"  {disk.mbr.size = }")

    for i, p in disk.partitions.items():
        print(f"\nPartition {i}:")
        print(f"  {p.begin_offset = }")
        print(f"  {p.cluster_size = }")
        print(f"  {p.clusters_begin_offset = }")
        print(f"  {len(p.files) = }")
        bytes_used = p.fats.get(1).number_of_used_clusters * p.cluster_size
        print(f"  {bytes_used = }")

        for j in p.fats.keys():
            print(f"\n  FAT{j}:")
            print(f"    {p.fats.get(j).begin_lba = }")
            print(f"    {p.fats.get(j).begin_offset = }")
            print(f"    {p.fats.get(j).size = }")
            print(f"    {p.fats.get(j).number_of_used_clusters = }")

        print(f"\n  Files:")
        for f in p.files:
            print(f"    {f.get_full_path() = }; {f.start_cluster = }; {f.size = }")


def main():
    # Build arguments and options list.
    description = "Volume ID sectors per FAT is wrong if partition is < 1GB in size."

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument(
        '-d', '--dir',
        action='store_true',
        help="List directories on disk."
    )
    parser.add_argument(
        '-i', '--info',
        action='store_true',
        help="Show disk info."
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help="List files on disk."
    )
    parser.add_argument(
        '-s', '--sort',
        action='store_true',
        help="Sort files in alphabetical order, folders first."
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Give verbose output."
    )
    # parser.add_argument(
    #     '-k', '--trim',
    #     nargs=2,
    #     type=str,
    #     help="Trim the file to keep content between given timestamps (HH:MM:SS)."
    # )
    # parser.add_argument(
    #     '-s', '--speed',
    #     type=float,
    #     help="Change the playback speed of the video using the given factor (0.5 to 100).",
    # )
    # parser.add_argument(
    #     '-t', '--tutorial',
    #     dest='rates',
    #     action='store_const',
    #     const=(128000, 500000, 10),
    #     default=(128000, 2000000, 25),
    #     help="Use lower bitrate and fewer fps for short tutorial videos."
    # )
    parser.add_argument(
        "device",
        nargs=1,
        help="Device to analyze or modify."
    )

    args = parser.parse_args()
    fat_disk = Disk(args.device[0])

    if args.dir:
        show_directories(fat_disk)
        exit()
    if args.info:
        show_info(fat_disk)
        exit()
    if args.list:
        list_files(fat_disk)
        exit()
    if args.sort:
        sort_files(fat_disk, args.verbose)
        exit()


if __name__ == '__main__':
    main()
