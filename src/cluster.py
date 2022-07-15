from device import ByteChunk
from util import bits_from_byte_int

class Cluster(ByteChunk):
    def __init__(self, hex_data, cluster_begin_lba=None):
        super().__init__(hex_data)

        self.begin_lba = cluster_begin_lba

class BaseEntry(ByteChunk):
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

class Dir(BaseEntry):

    # Structure:
    #   |  0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
    #   | SHORT FILENAME                 | A|  |  |     |
    #   |     |     | CHI |     |     | CLO | SIZE      |

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
        self.cluster = self.get_cluster()
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

    def get_cluster(self):
        index = self.bytes_to_int(self.get_cluster_low() + self.get_cluster_high())
        # Return "2" for root directory.
        return index if index != 0 else 2

    def is_end_of_dir(self):
        return self.get_bytes(0, 1) == b'\x00'

    def get_created_time(self):
        # TODO: Parse timestamps.
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

class LFN(BaseEntry):

    # Structure:
    #   |  0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
    #   | S| NAME-CHARS 1                |  |  |  | NAME-
    #   | CHARS 2                        |     | N-CH 3 |
    # NOTE for Sequence (S) (from Wikipedia):
    #   bit 6: last logical, first physical LFN entry, bit 5: 0; bits 4-0: number 0x01..0x14 (0x1F)

    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.long_filename = self.get_long_form_name()
        first_bits = self.get_logical_bits_from_byte(self.get_bytes(0, 1))
        self.seq_num = self.get_seq_num(first_bits)
        self.initial_lfn = self.get_initial_lfn(first_bits)

    def get_long_form_name(self):
        name_bytes = bytearray(self.get_bytes(1, 10) + self.get_bytes(14, 12) + self.get_bytes(28, 4))
        name_bytes = name_bytes.rstrip(b'\xff')
        name = name_bytes.decode('UTF-16')
        if name[-1] == '\x00':
            name = name[:-1]
        return name

    def get_seq_num(self, first_bits):
        # Sequence number is first 5 bits; i.e. up to "20" (0b10100).
        seq_bits = first_bits[:5]
        seq_num = int(seq_bits[::-1], 2)
        return seq_num

    def get_initial_lfn(self, first_bits):
        return True if first_bits[6] == 1 else False

    def get_logical_bits_from_byte(self, byte_value):
        # Logical bits are reverse order of physical bits.
        physical_bits = bits_from_byte_int(self.bytes_to_int(byte_value))
        return physical_bits[::-1]
