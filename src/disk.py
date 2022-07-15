from device import Device
from device import MBR
from device import PartitionTable
from partition import Partition


class Disk():
    def __init__(self, fat_device):
        self.fat_device = Device(fat_device)
        self.mbr = self.get_boot_sector()

        self.partitions = {}
        for p in range(1, 5):
            part_table = PartitionTable(self.mbr.partition_entries.get(p))
            if part_table.is_valid():
                self.partitions[p] = Partition(self.fat_device, part_table)

    def get_boot_sector(self, type='MBR'):
        # TODO: Assumes MBR.
        if type == 'MBR':
            boot_sector = MBR(self.fat_device.read_bytes(512))
        else:
            print(f"ERROR: {type} not supported.")
            exit(1)
        return boot_sector
