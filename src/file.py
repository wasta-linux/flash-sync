class File():
    def __init__(self, entry=None):
        # self.cluster_chain = []
        self.long_name = entry.long_filename if entry else None
        self.parents = []
        self.short_name = entry.short_filename
        self.start_cluster = entry.cluster
        self.size = entry.filesize
        self.type = 'directory' if 'directory' in entry.attribs else 'file'
        # self.type = 'directory' if 'directory' in entry.attribs or 'volume ID' in entry.attribs else 'file'

    def get_full_path(self):
        parent_path = '/' + '/'.join(self.parents[1:])
        if parent_path == '/':
            parent_path = ''
        path = f"{parent_path}/{self.long_name}"
        return path
