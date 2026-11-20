import os.path
import posixpath
import zipfile


class VirtualFileSystem:
    default_directory = '/'

    def __init__(self, zip_path: str):
        self.files = {}
        self.cwd = self.default_directory
        self.files[self.default_directory] = None

        if zip_path and os.path.exists(zip_path):
            self._init_zip(zip_path)
        else:
            print(f'Warning: VFS zip not found at: "{zip_path}". '
                  f'Current VFS will remain empty.')

    def _init_zip(self, zip_path: str):
        with zipfile.ZipFile(zip_path, 'r') as file:
            for info in file.infolist():
                path = self.default_directory + info.filename.strip('/')
                if info.is_dir():
                    self.files[path] = None
                else:
                    self.files[path] = file.read(info.filename)

        for path in list(self.files.keys()):
            parent = posixpath.dirname(path)
            while parent and parent not in self.files:
                self.files[parent] = None
                parent = posixpath.dirname(parent)

    def resolve_path(self, path: str):
        if not path.startswith("/"):
            path = posixpath.join(self.cwd, path)
        return posixpath.normpath(path)

    def read_file(self, path):
        resolved = self.resolve_path(path)
        if resolved in self.files and self.files[resolved] is not None:
            return self.files[resolved]
        return None

    def is_dir(self, path: str):
        resolved = self.resolve_path(path)
        return resolved in self.files and self.files[resolved] is None

    def exists(self, path: str):
        return self.resolve_path(path) in self.files

    def list_dir(self, path: str = '.'):
        target = self.resolve_path(path)
        if not self.is_dir(target): return None

        result = []
        for sub_path in self.files.keys():
            if sub_path == target: continue
            parent = posixpath.dirname(sub_path)
            if parent == target:
                entry = posixpath.basename(sub_path)
                if self.files[sub_path] is None: entry += '/'
                result.append(entry)

        result.sort()
        return result
