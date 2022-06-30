

def print_data(obj, title=None):
    if title:
        print(f"{title}:")
    obj.print_hex_data()
    print()

def print_attribs(obj, title=None):
    if title:
        print(f"{title}:")
    for k, v in obj.__dict__.items():
        print(f"{k} = {v}")
    print()

def get_lba_address_from_cluster(cluster_number, cluster_begin_lba, sectors_per_cluster):
    return cluster_begin_lba + (cluster_number - 2) * sectors_per_cluster
