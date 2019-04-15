import errno
import os
from gzip import open as gzip_open
from urllib.parse import urljoin


class HashFileCache(object):
    def __init__(self, root, url, gzip=False):
        self.root = root
        self.url = url
        self.gzip = gzip

    def create(self, hash):
        try:
            os.makedirs(os.path.join(self.root, hash))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def has_file(self, hash, file):
        return os.path.isfile(self.get_path(hash, file))

    def get_path(self, hash, file):
        return os.path.join(self.root, hash, file)

    def get_url(self, hash, file):
        return urljoin(self.url, '%s/%s' % (hash, file))

    def read_file(self, hash, file):
        return open(self.get_path(hash, file), 'rb')

    def read_data(self, hash, file):
        with self.read_file(hash, file) as f:
            return f.read()

    def cache_data(self, hash, file, data, url=True, gzip=True):
        if gzip and self.gzip:
            with gzip_open(self.get_path(hash, file + '.gz'), 'wb') as f:
                f.write(data)

        with open(self.get_path(hash, file), 'wb') as f:
            f.write(data)

        if url:
            return self.get_url(hash, file)
