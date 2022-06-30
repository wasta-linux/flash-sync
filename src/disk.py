import util

from device import ByteChunk
from device import MBR
from device import PartitionTable
from partition import FAT
from partition import VolumeID

class Disk():
    def __init__(self, fat_device):
        self.fat_device = fat_device
        with open(self.fat_device, 'rb') as d:
            self.mbr = MBR(d.read(512))

        self.partition_vol_ids = {}
        self.partition_calcs = {}
        self.partition_fats = {}
        self.partition_root_clusters = {}
        for p in range(1, 5):
            part_table = PartitionTable(self.mbr.partition_entries.get(p))
            self.set_partition_details(p, part_table)

    def set_partition_details(self, part_no, part_table):
        if part_table.is_valid():
            # Gather VolumeID details.
            with open(self.fat_device, 'rb') as d:
                d.seek((part_no - 1) * 512 + part_table.begin_lba * self.mbr.size)
                part_volume = VolumeID(d.read(512), part_table.begin_lba)
                self.partition_vol_ids[part_no] = part_volume
                self.partition_calcs[part_no] = {
                    'clusters_begin_offset': part_volume.cluster_begin_lba * part_volume.bytes_per_sector,
                    'root_dir_begin_offset': part_volume.root_dir_begin_lba * part_volume.bytes_per_sector,
                }
            # Gather FAT details.
            for f in range(1, 3):
                with open(self.fat_device, 'rb') as d:
                    d.seek(
                        part_volume.fat_begin_offset + (
                            (f - 1) * part_volume.sectors_per_fat * part_volume.bytes_per_sector
                        )
                    )
                    self.partition_fats[f] = FAT(
                        d.read(part_volume.sectors_per_fat * part_volume.bytes_per_sector),
                        part_volume.fat_begin_lba
                    )
            # Gather root cluster details.
            with open(self.fat_device, 'rb') as d:
                d.seek(part_volume.root_dir_begin_lba * part_volume.bytes_per_sector)
                self.partition_root_clusters[part_no] = ByteChunk(
                    d.read(part_volume.sectors_per_cluster * part_volume.bytes_per_sector)
                )
