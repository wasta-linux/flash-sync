from device import ByteChunk

class Base(ByteChunk):
    def __init__(self, hex_data):
        super().__init__(hex_data)

        self.deleted = self.is_deleted()
        self.empty = self.is_empty()
        self.cluster_low = self.get_cluster_low()

    def is_deleted(self):
        return self.get_bytes(0, 1) == '\xe5'

    def is_empty(self):
        return self.get_bytes(0, 1) == b'\x00'

    def is_long_form_name(self):
        return self.get_bytes(0x0c, 1) == b'\x00' and self.get_bytes(0x0b, 1) == b'\x0f'

    def get_cluster_low(self):
        return self.bytes_to_int(self.get_bytes(26, 2))

class Dir(Base):
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

    def is_deleted(self):
        return self.get_bytes(0, 1) == hex(0xe5)

    def is_end_of_dir(self):
        return self.get_bytes(0, 1) == hex(0x00)

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
        return self.bytes_to_int(self.get_bytes(20, 2))

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
