import os


class SemanticFS:

    def __init__(self, datastore_root):
        self._dsroot = datastore_root

    @staticmethod
    def _is_tag_name(name):
        return name.startswith('_')

    def _datastore_path(self, virtualpath):

        # Redirect semantic paths to the entry point root (remove tags from path)
        # FIXME Normalizzare path (os.altsep => os.sep, relative => absolute)
        # /a/_b/_c/x -> dsroot/a/_b/x
        # /a/_b/_c/ -> dsroot/a/_b/_c/
        # /a/_b/_c/_d/ -> dsroot/a/_b/_d/

        components = virtualpath.split(os.sep)
        tmppath = []
        for i, name in components:
            if i == 0 or i == 1:
                tmppath.append(name)
            else:
                if self._is_tag_name(tmppath[i-2]) and self._is_tag_name(tmppath[i-1]):
                    # _a/_b/_c => _a/_c
                    # _a/_b/x => _a/x
                    del tmppath[-1]
                tmppath.append(name)

        tmppath = os.sep.join(tmppath)
        if tmppath.startswith("/"):
            tmppath = tmppath[1:]

        path = os.path.join(self._dsroot, tmppath)

        return path

    def _exists(self, path):
        pass

    def access(self, path, mode):
        #if not self._exists(path):
        #    return False

        dspath = self._datastore_path(path)
        return os.access(dspath, mode)

    def getattr(self, path, fh=None):
        dspath = self._datastore_path(path)
        return os.lstat(dspath)

    # File methods
    # ============

    def open(self, path, flags):
        if not self._exists(path):
            return False

        dspath = self._datastore_path(path)
        return os.open(dspath, flags)