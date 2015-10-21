import os

from semanticfolder import SemanticFolder


class SemanticFS:

    def __init__(self, datastore_root):
        self._dsroot = datastore_root

    @staticmethod
    def _is_tag_name(name):
        return name.startswith('$')

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

    @staticmethod
    def _semantic_path_info(self, path) -> list:
        """

        :param path: a virtual path
        :return: [ {entrypoint: "/a/_b" (a virtual path), tags: ["_c", "_d", "_e"], file: "x" }, ... ]
        """
        info = []
        components = os.path.normpath(path).split(os.sep)
        state = 0

        for i, name in components:

            if state == 0:
                # Searching an entry point
                if self._is_tag_name(name):
                    info.append({ 'entrypoint': os.sep.join(components[0:i+1]), 'tags': [], 'file': '' })
                    state = 1

            elif state == 1:
                # Collecting all the tags and the final file/folder (if there is one)
                if self._is_tag_name(name):
                    info[-1]['tags'].append(name)
                else:
                    info[-1]['file'] = name
                    state = 0

        return info

    def _get_semantic_folder(self, path):
        storedir = self._datastore_path(path)
        graph_file = os.path.join(storedir, '$$_SEMANTIC_FS_GRAPH_FILE_$$')
        assoc_file = os.path.join(storedir, '$$_SEMANTIC_FS_ASSOC_FILE_$$')
        return SemanticFolder.from_filename(graph_file, assoc_file, path)

    def _exists(self, path) -> bool:
        """

        :param path: a virtual path
        :return:
        """
        for info in self._semantic_path_info(path):
            folder = self._get_semantic_folder(info['entrypoint'])
            if not (folder.graph.has_path(info['tags']) and folder.filetags.has_tags(info['file'], info['tags'])):
                return False

        return True

    def access(self, path, mode):
        if not self._exists(path):
            return False

        dspath = self._datastore_path(path)
        return os.access(dspath, mode)

    def chmod(self, path, mode):
        if not self._exists(path):
            raise FileNotFoundError(path + ' not found.')

        dspath = self._datastore_path(path)
        return os.chmod(dspath, mode)

    def chown(self, path, uid, gid):
        if not self._exists(path):
            raise FileNotFoundError(path + ' not found.')

        dspath = self._datastore_path(path)
        return os.chown(dspath, uid, gid)

    def lstat(self, path):
        if not self._exists(path):
            raise FileNotFoundError(path + ' not found.')

        dspath = self._datastore_path(path)
        return os.lstat(dspath)

    def readdir(self, path):
        pass

    # File methods
    # ============

    def open(self, path, flags):
        if not self._exists(path):
            return False

        dspath = self._datastore_path(path)
        return os.open(dspath, flags)