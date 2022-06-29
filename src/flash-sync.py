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

# import fs
# import pyfatfs
import sys
import device
import partition

# from fs.walk import Walker

def print_attribs(obj, title=None):
    if title:
        print(f"{title}:")
    for k, v in obj.__dict__.items():
        print(f"{k} = {v}")
    print()

def print_data(obj, title=None):
    if title:
        print(f"{title}:")
    obj.print_hex_data()
    print()

def get_lba_address_from_cluster(cluster_number, cluster_begin_lba, sectors_per_cluster):
    return cluster_begin_lba + (cluster_number - 2) * sectors_per_cluster


# Disk layout:
#   MBR - 1 sector
#   Partitions - rest of drive
#       FSInfo/VolumeID - 1 sector
#       FATs - ?
#       data - rest of partition


fat_device = sys.argv[1]
# with fs.open_fs(f"fat://{fat_device}") as fat_fs:
    # print(dir(fat_fs))
    # print(dir(fat_fs.fs))
    # print(fat_fs.fs.bpb_header)
    # print(len(fat_fs.fs.fat))
    # for d in fat_fs.listdir('/'):
        # print(fat_fs.listdir(d))
    # for path in walker.files(fat_fs):
    #     print(path)
    # for path in fat_fs.walk.files():
    #     print(path)
    # for path, info in fat_fs.walk.info():
        # print(path, info)
        # print(fat_fs.getospath(path))

# Details of MBR.
#   TODO: What if it's GPT? Is this possible?
# print("Analyzing MBR sector...")
with open(fat_device, 'rb') as d:
    mbr_sector = device.MBR(d.read(512))

# print_data(mbr_sector, 'MBR sector')
p1_table = device.PartitionTable(mbr_sector.partition1)
p2_table = device.PartitionTable(mbr_sector.partition2)
p3_table = device.PartitionTable(mbr_sector.partition3)
p4_table = device.PartitionTable(mbr_sector.partition4)
# print_attribs(p1_table, "Partition table 1")

# Details of 1st partition.
# print("Analyzing 1st partition...")
## Details of FS Info/VolumeID sector.
# Get sector from drive.
with open(fat_device, 'rb') as d:
    d.seek(p1_table.begin_lba * mbr_sector.size)
    p1_sector = partition.VolumeID(d.read(512), p1_table.begin_lba) if p1_table.is_valid() else None
    p2_sector = partition.VolumeID(d.read(512), p2_table.begin_lba) if p2_table.is_valid() else None
    p3_sector = partition.VolumeID(d.read(512), p3_table.begin_lba) if p3_table.is_valid() else None
    p4_sector = partition.VolumeID(d.read(512), p4_table.begin_lba) if p4_table.is_valid() else None

# print_data(pi_sector, "FS Info/VolumeID sector")

# Details of FATs.
fat_begin_offset = p1_sector.fat_begin_lba * p1_sector.bytes_per_sector
total_fat_length = p1_sector.number_of_fats * p1_sector.sectors_per_fat * p1_sector.bytes_per_sector
# print(f"{total_fat_length = }")
# print(f"{fat_begin_offset = }")
# print_attribs(p1_sector)

# Details of data clusters.
root_dir_begin_lba = get_lba_address_from_cluster(
    p1_sector.root_dir_first_cluster,
    p1_sector.cluster_begin_lba,
    p1_sector.sectors_per_cluster,
)
clusters_begin_offset = p1_sector.cluster_begin_lba * p1_sector.bytes_per_sector
root_dir_begin_offset = root_dir_begin_lba * p1_sector.bytes_per_sector
# print(f"{clusters_begin_offset = }")
# print(f"{root_dir_begin_lba = }")
# print(f"{root_dir_begin_offset = }")

# Get FAT info for 1st partition.
with open(fat_device, 'rb') as d:
    d.seek(fat_begin_offset)
    fat1 = partition.FAT(
        d.read(p1_sector.sectors_per_fat * p1_sector.bytes_per_sector),
        p1_sector.fat_begin_lba
    )
    fat2 = partition.FAT(
        d.read(p1_sector.sectors_per_fat * p1_sector.bytes_per_sector),
        p1_sector.fat_begin_lba + p1_sector.sectors_per_fat * p1_sector.bytes_per_sector
    )
print_attribs(fat1, "FAT32 Table 1")
print(fat1.clusters)
print(fat2.clusters)
exit()
# print("FAT initial chunks:")
# chunk_count = 8
# for c in range(chunk_count):
#     print(f"{c+1}: {fat1.get_bytes(c*4, 4)}")
# print()

print(f"Analyzing clusters...")
with open(fat_device, 'rb') as d:
    d.seek(root_dir_begin_lba * p1_sector.bytes_per_sector)
    root_cluster = device.ByteChunk(d.read(p1_sector.sectors_per_cluster * p1_sector.bytes_per_sector))

# print_data(root_cluster, "Root cluster")
number_of_entries = int(root_cluster.length / 32)

entries = {}
long_filename = ''
for i in range(number_of_entries):
    # print(f"Entry {i+1}:")
    entry_i = partition.Base(root_cluster.get_bytes(i*32, 32))
    # entry.print_hex_data()
    # print(entry.__dict__)
    if entry_i.is_long_form_name():
        entry_i = partition.LFN(root_cluster.get_bytes(i*32, 32))
        long_filename = entry_i.long_filename + long_filename
        # print(f"{entry.long_filename=}")
    elif entry_i.is_empty():
        # print(f"Entry {i+1} is empty")
        continue
    else:
        entry_i = partition.Dir(root_cluster.get_bytes(i*32, 32))
        entry_i.long_filename = long_filename
        # print_data(entry_i, f"Entry {i+1}")
        # print_attribs(entry_i)
        long_filename = ''
    entries[i+1] = entry_i

for k, v in entries.items():
    print(f"{k}: {v}")
