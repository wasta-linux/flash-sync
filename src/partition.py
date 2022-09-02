import config
from cluster import BaseEntry
from cluster import Cluster
from cluster import Dir
from cluster import LFN
from device import ByteChunk
from device import SignedSector
from file import File
from util import chunker
from util import get_lba_address_from_cluster
from util import print_attribs


class Partition():
    def __init__(self, fat_device, part_table):
        self.begin_offset = part_table.begin_lba * part_table.sector_size
        if config.VERBOSE:
            print(f"Initializing partition at offset {self.begin_offset}.")
        # Gather VolumeID details.
        self.volume_id = VolumeID(
            fat_device.read_bytes(part_table.sector_size, self.begin_offset),
            part_table.begin_lba
        )
        self.cluster_size = self.volume_id.bytes_per_sector * self.volume_id.sectors_per_cluster
        self.clusters_begin_offset = self.volume_id.cluster_begin_lba * self.volume_id.bytes_per_sector
        self.root_dir_begin_offset = self.volume_id.root_dir_begin_lba * self.volume_id.bytes_per_sector
        self.entry_size = 32

        # Gather FAT details.
        self.fats = {}
        for f in range(1, 3):
            if config.VERBOSE:
                print(f"Gathering info from FAT{f}.")
            read_length = self.volume_id.sectors_per_fat * self.volume_id.bytes_per_sector
            base_lba = int(self.volume_id.fat_begin_offset / self.volume_id.bytes_per_sector)
            begin_lba = base_lba + (f - 1) * self.volume_id.sectors_per_fat
            seek_length = begin_lba * self.volume_id.bytes_per_sector
            fat_bytes = fat_device.read_bytes(read_length, seek_length)
            self.fats[f] = FAT(fat_device, fat_bytes, begin_lba)

        # Build file and directory lists (in disk order).
        if config.VERBOSE:
            print(f"Getting list of partition files.")
        self.files = self.get_file_list(fat_device)
        self.dir_cluster_indexes = self.get_dir_cluster_indexes(fat_device)
        self.directories = self.get_dir_list(fat_device)

    def get_file_list(self, device, files=list()):
        if config.VERBOSE:
            print(f"Getting child entries starting in cluster {self.volume_id.root_dir_first_cluster}")
        root_cluster_chain = self.get_chain(device, self.volume_id.root_dir_first_cluster)
        if config.VERBOSE:
            print(f"Cluster chain: {root_cluster_chain}")
        entries = []
        for c in root_cluster_chain:
            entries.extend(self.get_child_entries(device, c))
        if config.VERBOSE:
            print(f"Found {len(entries)} entries.")
        return self.get_files_from_entries(device, files, ['/'], entries)

    def get_child_entries(self, device, cluster_index):
        cluster = Cluster(
            self.get_cluster_bytes(device, cluster_index),
            self.volume_id.cluster_begin_lba
        )
        return self.get_entries_from_cluster(cluster)

    def get_files_from_entries(self, device, files, parent_path, entries):
        if config.VERBOSE:
            print(f"Gathering file info from {'/'.join(parent_path)}")
        long_name = ''
        for i, e in enumerate(entries):
            if config.VERBOSE:
                print(f"Reading entry {i+1}")
            if not e.is_deleted():
                if e.is_empty():
                    if config.VERBOSE:
                        print(f"This entry has been deleted.")
                    continue
                elif e.is_long_form_name():
                    if config.VERBOSE:
                        print(f"This is a long-form name entry.")
                    entry = LFN(e.hex_data)
                    long_name = entry.long_filename + long_name
                else:
                    if config.VERBOSE:
                        print(f"This is a file/directory entry.")
                    entry = Dir(e.hex_data)
                    if entry.short_filename.rstrip() == '.' or entry.short_filename.rstrip() == '..':
                        # Skip "." and ".." dir shortcut.
                        continue
                    entry.long_filename = long_name
                    long_name = '' # reset
                    node = File(entry)
                    node.parents = parent_path[:]
                    files.append(node)
                    if node.type == 'directory':
                        # Recurse into directory.
                        child_entries = self.get_child_entries(device, entry.cluster)
                        files = self.get_files_from_entries(
                            device,
                            files,
                            parent_path + [entry.long_filename],
                            child_entries
                        )
        if config.VERBOSE:
            print(f"Files found: {', '.join([f.short_name for f in files])}")
        return files

    def get_dir_list(self, device):
        dir_groups = {}
        for i in self.dir_cluster_indexes:
            cluster_chain = self.get_chain(device, i)
            if config.VERBOSE:
                print(f"Cluster index: {i}; cluster chain: {', '.join([str(c) for c in cluster_chain])}")
            entries = self.get_entries_from_chain(device, cluster_chain.copy())
            file_groups, deleted_count = self.split_entries_into_file_groups(entries)
            dir_groups[i] = {
                'chain': cluster_chain,
                'deleted-count': deleted_count,
                'files': file_groups,
            }
        return dir_groups

    def get_chain(self, device, i):
        # Get full cluster chain.
        chain = [i]
        end = False
        next = chain[-1]
        while not end:
            next = self.get_next_cluster_index(device, next)
            if config.VERBOSE:
                print(f"Next cluster index: {next}")
            if next is None:
                end = True
            else:
                if config.VERBOSE:
                    print(f"Cluster chain: {chain}")
                chain.append(next)
        return chain

    def get_dir_cluster_indexes(self, device, indexes=list(), cluster_index=None):
        if cluster_index is None:
            cluster_index = self.volume_id.root_dir_first_cluster
        entries = self.get_child_entries(device, cluster_index)
        for e in entries:
            if not e.is_deleted():
                if e.is_empty():
                    continue
                elif e.is_long_form_name():
                    continue
                else:
                    entry = Dir(e.hex_data)
                    if entry.short_filename.rstrip() == '.' or entry.short_filename.rstrip() == '..':
                        # Skip "." and ".." dir shortcut.
                        continue
                    if 'volume ID' in entry.attribs:
                        indexes.append(entry.cluster)
                    if 'directory' in entry.attribs:
                        indexes.append(entry.cluster)
                        # Recurse into directory.
                        indexes = self.get_dir_cluster_indexes(device, indexes, entry.cluster)
        return indexes

    def split_entries_into_file_groups(self, entries):
        file_entry_groups = {}
        group = []
        long_name = ''
        lfn_count = 0
        deleted_count = 0
        for i, e in enumerate(entries):
            if e.is_deleted():
                deleted_count += 1          # count deleted dir entry
                deleted_count += lfn_count  # count LFN entries for deleted dir entries
            else:
                if e.is_empty():
                    continue
                elif e.is_long_form_name():
                    lfn_count += 1
                    entry = LFN(e.hex_data)
                    group.append(entry)
                    long_name = entry.long_filename + long_name
                else:
                    entry = Dir(e.hex_data)
                    entry.long_filename = long_name
                    group.append(entry)
                    n = entry.long_filename if entry.long_filename else entry.short_filename
                    file_entry_groups[n] = group
                    long_name = ''
                    lfn_count = 0
                    group = []
        return file_entry_groups, deleted_count

    def get_entries_from_chain(self, device, chain):
        entries = []
        while chain:
            cluster = self.get_cluster_obj(device, chain.pop(0))
            entries.extend(self.get_entries_from_cluster(cluster))
        return entries

    def get_entries_from_cluster(self, cluster_obj):
        entries = chunker(cluster_obj.hex_data, 32)
        return [BaseEntry(e) for e in entries]

    def get_cluster_bytes(self, device, cluster_index):
        return device.read_bytes(self.cluster_size, self.get_cluster_offset(cluster_index))

    def get_cluster_obj(self, device, cluster_index):
        return Cluster(self.get_cluster_bytes(device, cluster_index))

    def get_next_cluster_index(self, device, cluster_index):
        next_indexes = {
            1: None,
            2: None,
        }
        for i, f in self.fats.items():
            next_index = f.get_next_cluster_index(device, cluster_index)
            next_indexes[i] = next_index
        if next_indexes.get(1) != next_indexes.get(2):
            print(f"WARNING: Entry in FAT1 does not match entry in FAT2")
        return next_indexes.get(1)

    def get_cluster_offset(self, cluster_index):
        return self.clusters_begin_offset + (cluster_index - 2) * self.cluster_size

    def set_cluster_chain_entries(self, device, cluster_chain, entries, deleted_count):
        entries_copy = entries.copy()
        num_entries_per_cluster = self.cluster_size / self.entry_size
        if len(entries_copy) > len(cluster_chain) * num_entries_per_cluster:
            print(f"ERROR: Too many entries for reserved space.")
            return
        # Store new data in memory before writing it all at once.
        new_data = {}
        for c in cluster_chain:
            new_data[c] = {}
            c_offset = self.get_cluster_offset(c)
            i = 0
            while entries_copy and i < num_entries_per_cluster:
                e = entries_copy.pop(0)
                seek_length = c_offset + self.entry_size * i
                new_data[c][seek_length] = e.hex_data
                i += 1
            while deleted_count > 0 and len(new_data[c]) < num_entries_per_cluster:
                # Add 0-byte entries in place of deleted file clusters.
                seek_length = c_offset + self.entry_size * i
                new_data[c][seek_length] = b'\x00' * self.entry_size
                deleted_count -= 1
                i += 1
        # Write out new data.
        if config.VERBOSE:
            print(f"Written bytes for chain {cluster_chain}:")
        for c, seeks in new_data.items():
            for s, data in seeks.items():
                if config.VERBOSE:
                    ByteChunk(data).hexdump(s)
                device.write_bytes(data, s)

class VolumeID(SignedSector):
    def __init__(self, hex_data, lba_begin=0):
        super().__init__(hex_data)

        self.begin_lba = lba_begin
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
        # TODO: Seems to only be 2 bytes long (not 4) if partition is < 1GB.
        try:
            sector_count = self.bytes_to_int(self.get_bytes(0x24, 4))
        except MemoryError:
            print(f"ERROR: MemoryError. Check if partition is < 1GB.")
            exit(1)
        return sector_count

    def get_root_cluster(self):
        return self.bytes_to_int(self.get_bytes(44, 4))

class FAT(ByteChunk):
    def __init__(self, device, hex_data, begin_lba=0):
        super().__init__(hex_data)

        self.begin_lba = begin_lba
        self.begin_offset = self.begin_lba * device.sector_size
        self.id = self.get_id() # first 4 bytes: 0xf0 (non-partitioned) or 0xf8 (partitioned)
        self.end_of_chain_marker = self.get_end_of_chain_marker()
        self.cluster_size = 4 # for all FAT32
        self.number_of_used_clusters = self.get_number_of_used_clusters()

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

    def get_fat_entry(self, device, cluster_index):
        seek_length = self.begin_offset + cluster_index * self.cluster_size
        return device.read_bytes(self.cluster_size, seek_length)

    def get_next_cluster_index(self, device, cluster_index):
        next_index = None
        fat_entry = self.get_fat_entry(device, cluster_index)
        if fat_entry != self.end_of_chain_marker and fat_entry != self.id:
            next_index = self.bytes_to_int(fat_entry)
        return next_index
