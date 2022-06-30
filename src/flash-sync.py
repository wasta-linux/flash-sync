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

import sys
import disk

# Disk layout:
#   MBR - 1 sector
#   Partitions - rest of drive
#       FSInfo/VolumeID - 1 sector
#       FATs - ?
#       data - rest of partition


fat_device = sys.argv[1]
fat_disk = disk.Disk(fat_device)
fat_disk.partition_root_clusters.get(1).print_hex_data()
exit()
