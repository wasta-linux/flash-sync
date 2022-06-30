from device import SignedSector
from device import ByteChunk
from util import get_lba_address_from_cluster


class Base(ByteChunk):
    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.deleted = self.is_deleted()
        self.empty = self.is_empty()
        self.cluster_low = self.get_cluster_low()

    def is_deleted(self):
        return self.get_bytes(0, 1) == b'\xe5'

    def is_empty(self):
        return self.get_bytes(0, 1) == b'\x00'

    def is_long_form_name(self):
        return self.get_bytes(0x0c, 1) == b'\x00' and self.get_bytes(0x0b, 1) == b'\x0f'

    def get_cluster_low(self):
        return self.get_bytes(26, 2)

class Entry(Base):
    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.attribs = self.get_attribs()
        if 'volume ID' not in self.attribs and 'directory' not in self.attribs:
            # regular file
            self.short_filename = self.get_short_filename(8)
            self.extension = self.get_extension()
        else:
            # directory
            self.short_filename = self.get_short_filename(11)
            self.extension = None
        self.cluster_high = self.get_cluster_high()
        self.cluster = self.bytes_to_int(self.cluster_low + self.cluster_high)
        self.lba_address = get_lba_address_from_cluster(
            self.cluster,

        )
        self.filesize = self.get_filesize()
        self.long_filename = None

    def get_short_filename(self, end):
        return self.get_bytes(0, end).decode()

    def get_extension(self):
        return self.get_bytes(8, 3).decode()

    def get_attribs(self):
        attribs = []
        attribs_ref = {
            1: 'read only',     # 2**0
            2: 'hidden',        # 2**1
            4: 'system',        # 2**2
            8: 'volume ID',     # 2**3
            16: 'directory',    # 2**4
            32: 'archive',      # 2**5
            64: 'unused [0]',   # 2**6
            128: 'unused [0]',  # 2**7
        }
        value = self.bytes_to_int(self.get_bytes(11, 1))
        keys = [k for k in attribs_ref.keys()]
        keys.reverse()
        for k in keys:
            if value >= k:
                attribs.append(attribs_ref.get(k))
                value -= k
        return attribs

    def is_end_of_dir(self):
        # return self.get_bytes(0, 1) == hex(0x00)
        return self.get_bytes(0, 1) == b'\x00'

    def get_created_time(self):
        time_ref = {
            2**0: 1,       # bi-seconds
            2**1: 2,
            2**2: 4,
            2**3: 8,
            2**4: 16,
            2**5: 1,        # minutes
            2**6: 2,
            2**7: 4,
            2**8: 8,
            2**9: 16,
            2**10: 32,
            2**11: 1,       # hours
            2**12: 2,
            2**13: 4,
            2**14: 8,
            2**15: 16,
        }
        # value = int(self.get_bytes(15, 2))
        # timestamp = f""
        return None

    def get_cluster_high(self):
        return self.get_bytes(20, 2)

    def get_filesize(self):
        return self.bytes_to_int(self.get_bytes(28, 4))

class LFN(Base):
    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.long_filename = self.get_long_form_name()
        self.seq_num = self.get_seq_num()

    def get_seq_num(self):
        return self.bytes_to_int(self.get_bytes(0, 1))

    def get_long_form_name(self):
        name_bytes = bytearray(self.get_bytes(1, 10) + self.get_bytes(14, 12) + self.get_bytes(28, 4))
        name_bytes = name_bytes.rstrip(b'\xff')
        name = name_bytes.decode('UTF-16')
        if name[-1] == '\x00':
            name = name[:-1]
        return name

class VolumeID(SignedSector):
    def __init__(self, hex_data, lba_begin=0):
        super().__init__(hex_data)

        self.begin_lba = lba_begin
        # self.begin_signature = self.get_begin_signature()
        self.end_signature = self.get_end_signature()

        self.bytes_per_sector = self.get_bytes_per_sector()
        self.reserved_sector_count = self.get_reserved_sector_count()
        self.number_of_fats = self.get_number_of_fats()
        self.sectors_per_fat = self.get_sectors_per_fat()

        self.fat_begin_lba = self.begin_lba + self.reserved_sector_count
        self.cluster_begin_lba = self.fat_begin_lba + (self.number_of_fats * self.sectors_per_fat)
        self.sectors_per_cluster = self.get_sectors_per_cluster()
        self.root_dir_first_cluster = self.get_root_cluster()

        self.root_dir_begin_lba = get_lba_address_from_cluster(
            self.root_dir_first_cluster,
            self.cluster_begin_lba,
            self.sectors_per_cluster,
        )
        self.fat_begin_offset = self.fat_begin_lba * self.bytes_per_sector
        self.total_fat_length = self.number_of_fats * self.sectors_per_fat * self.bytes_per_sector

    def get_bytes_per_sector(self):
        return self.bytes_to_int(self.get_bytes(11, 2))

    def get_sectors_per_cluster(self):
        return self.bytes_to_int(self.get_bytes(0x0d, 1))

    def get_reserved_sector_count(self):
        return self.bytes_to_int(self.get_bytes(0x0e, 2))

    def get_number_of_fats(self):
        return self.bytes_to_int(self.get_bytes(0x10, 1))

    def get_sectors_per_fat(self):
        return self.bytes_to_int(self.get_bytes(0x24, 4))

    def get_root_cluster(self):
        return self.bytes_to_int(self.get_bytes(44, 4))

class FAT(ByteChunk):
    def __init__(self, hex_data, begin_lba=0):
        super().__init__(hex_data)

        self.hex_data = self.hex_data[:1024]
        self.begin_lba = begin_lba
        self.id = self.get_id() # first 4 bytes: 0xf0 (non-partitioned) or 0xf8 (partitioned)
        self.end_of_chain_marker = self.get_end_of_chain_marker()
        self.cluster_size = 4 # for all FAT32
        self.number_of_used_clusters = self.get_number_of_used_clusters()
        self.clusters = self.get_used_clusters()

    def get_id(self):
        return self.get_bytes(0, 4)

    def get_end_of_chain_marker(self):
        return self.get_bytes(4, 4)

    def get_used_clusters(self):
        all_bytes = bytearray(self.hex_data)
        used_bytes = all_bytes.rstrip(b'\x00')
        used_clusters = {}
        i = 0
        while used_bytes:
            used_clusters[i] = used_bytes[:4]
            used_bytes = used_bytes[4:]
            i += 1
        return used_clusters

    def get_number_of_used_clusters(self):
        all_bytes = bytearray(self.hex_data)
        used_bytes = all_bytes.rstrip(b'\x00')
        return int(len(used_bytes) / 4)
