import config

def print_data(obj, title=None):
    if title:
        print(f"{title}:")
    obj.hexdump()
    print()

def print_attribs(obj, title=None):
    if title:
        print(f"{title}:")
    for k, v in obj.__dict__.items():
        print(f"{k} = {v}")
    print()

def get_lba_address_from_cluster(cluster_number, cluster_begin_lba, sectors_per_cluster):
    return cluster_begin_lba + (cluster_number - 2) * sectors_per_cluster

def chunker(seq, size):
    # Ref: https://stackoverflow.com/a/434328
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def bits_from_byte_int(int_value):
    offset = 2
    return bin(int_value)[offset:].zfill(8)

def sort_dir_groups(device, dir_groups):
    sorted_dir_groups = {}
    for c, d in dir_groups.items():
        sorted_dir_groups[c] = {
            'chain': d.get('chain'),
            'deleted-count': d.get('deleted-count'),
            'files': [],
        }
        dirs = {}
        files = {}
        if config.VERBOSE:
            print(f"Existing bytes for chain {d.get('chain')}:")
        for n, g in d.get('files').items():
            attribs = g[-1].attribs
            if config.VERBOSE:
                for e in g:
                    e.hexdump()
            type = 'unknown'
            if 'directory' in attribs:
                type = 'directory'
            elif 'archive' in attribs:
                type = 'file'
            elif 'volume ID' in attribs:
                type = 'root'
            if type == 'directory':
                dirs[n] = g
            elif type == 'file':
                files[n] = g
            elif type == 'root':
                # Add root entry first.
                sorted_dir_groups[c]['files'].append([n, g])
        for n in sorted(dirs.keys(), key=str.lower):
            sorted_dir_groups[c]['files'].append([n, dirs.get(n)])
        for n in sorted(files.keys(), key=str.lower):
            sorted_dir_groups[c]['files'].append([n, files.get(n)])

    return sorted_dir_groups
