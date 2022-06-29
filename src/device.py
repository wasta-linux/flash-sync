
class ByteChunk():
    def __init__(self, hex_data):
        self.hex_data = hex_data
        self.length = len(self.hex_data)
        self.size = self.length

    def print_hex_data(self, start=0, end=None):
        o = 0
        for i, b in enumerate(self.hex_data[start:end]):
            if i % 16 == 0:
                print(f"{o:08x}  {b:02x} ", end='')
                o += 0x10
            elif i % 16 == 15:
                print(f"{b:02x} ")
            elif i % 16 == 7:
                print(f"{b:02x}  ", end='')
            elif i == len(self.hex_data[start:end]) - 1:
                print()
            else:
                print(f"{b:02x} ", end='')

    def get_bytes(self, offset, length):
        return self.hex_data[offset:offset+length]

    def bytes_to_hex(self, little_endian_bytes, end='little'):
        return hex(self.bytes_to_int(little_endian_bytes, end=end))

    def bytes_to_int(self, little_endian_bytes, end='little'):
        if end == 'little':
            value = int(''.join(format(b, '02x') for b in little_endian_bytes[::-1]), 16)
        elif end == 'big':
            value = int(''.join(format(b, '02x') for b in little_endian_bytes), 16)
        return value

class Sector(ByteChunk):
    def __init__(self, hex_data, sector_size=512):
        super().__init__(hex_data)

        self.size = sector_size

        if not self.is_correct_size():
            print(f"ERROR: Incorrect sector size: {len(hex_data)}. Expected {self.sector_size}")
            exit(1)

    def is_correct_size(self):
        return len(self.hex_data) == self.size

class PartitionTable(ByteChunk):
    def __init__(self, hex_data, sector_size=512):
        super().__init__(hex_data)

        self.begin_lba = self.get_begin_lba()

        self.sector_size = sector_size
        self.boot_flag = self.get_boot_flag()
        self.chs_begin = self.get_chs_begin()
        self.type_code = self.get_type_code()
        self.chs_end = self.get_chs_end()
        self.number_of_sectors = self.get_number_of_sectors()
        self.partition_size = self.number_of_sectors * self.sector_size

    def get_boot_flag(self):
        return self.bytes_to_hex(self.get_bytes(0, 1))

    def get_chs_begin(self):
        return self.bytes_to_hex(self.get_bytes(1, 3))

    def get_type_code(self):
        return self.bytes_to_hex(self.get_bytes(4, 1))

    def get_chs_end(self):
        return self.bytes_to_hex(self.get_bytes(5, 3))

    def get_begin_lba(self):
        return self.bytes_to_int(self.get_bytes(8, 4))

    def get_number_of_sectors(self):
        return self.bytes_to_int(self.get_bytes(12, 4))

    def is_valid(self):
        return self.type_code == hex(0x0b) or self.type_code == hex(0x0c)

class SignedSector(Sector):
    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.end_signature = self.get_end_signature()

        if not self.is_valid_sector():
            print(f"ERROR: Incorrect end signature: {self.end_signature}. Expected: {hex(0x55aa)}")
            self.print_hex_data()
            exit(1)

    def get_end_signature(self):
        return self.bytes_to_hex(self.get_bytes(510, 2), end='big')

    def is_valid_sector(self):
        return self.end_signature == hex(0x55aa)

class MBR(SignedSector):
    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.partition1 = self.get_partition_bytes(1)
        self.partition2 = self.get_partition_bytes(2)
        self.partition3 = self.get_partition_bytes(3)
        self.partition4 = self.get_partition_bytes(4)

    def get_partition_bytes(self, part_num):
        return self.get_bytes(446+16*(part_num-1), 16)

"""=========================================================================="""

class FileSystem():
    m_rootDir = ''

    def initFDT(self):
        pass

    def sort(self):
        pass

class VolumeAccess():
    FAT_END_CHAIN = ''
    m_bootSector = ''
    m_FAT1Data = ''
    m_FAT2Data = ''
    m_hDevice = ''

    def initData(self):
        pass

    def lockAndUnmount(self):
        pass

    def readChainedClusters(self):
        pass

    def writeChainedClusters(self):
        pass

def isDeletedEntry(aEntryToCheck):
    return aEntryToCheck.DIR_Name[0] == char(0xE5)
