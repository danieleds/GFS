#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno
import logging

from fuse import FUSE, FuseOSError, Operations

from semanticfolder import SemanticFolder

logger = logging.getLogger('SemanticFSLogger')
logger.setLevel(logging.DEBUG)


class SemanticFS(Operations):
    def __init__(self, datastore_root):
        self._dsroot = datastore_root
        # self.root = datastore_root

    # Helpers
    # =======

    @staticmethod
    def _is_semantic_name(name):
        return name.startswith('$')

    @staticmethod
    def _is_tag(path):
        components = os.path.normpath(path).split(os.sep)
        return len(components) >= 2 \
               and SemanticFS._is_semantic_name(components[-1]) \
               and SemanticFS._is_semantic_name(components[-2])

    @staticmethod
    def _is_entrypoint(path):
        components = os.path.normpath(path).split(os.sep)
        if len(components) == 1 and SemanticFS._is_semantic_name(components[-1]):
            return True
        elif len(components) >= 2 and SemanticFS._is_semantic_name(components[-1]) \
                and not SemanticFS._is_semantic_name(components[-2]):
            return True
        else:
            return False

    @staticmethod
    def _is_semantic_file(path):
        """
        /a/_b/_c -> false (it's a tag)
        /a/_b/_c/ -> false (it's a tag)
        /a/_b -> false (it's an entry point)
        /a/_b/ -> false (it's an entry point)
        /a/b -> false
        /a/b/ -> false
        /a/_b/x -> true
        /a/_b/_c/x -> true
        /a/_b/d/ -> true
        /a/_b/_c/d/ -> true
        :param path:
        :return:
        """
        components = os.path.normpath(path).split(os.sep)
        return len(components) >= 2 \
               and not SemanticFS._is_semantic_name(components[-1]) \
               and SemanticFS._is_semantic_name(components[-2])

    def _datastore_path(self, virtualpath):

        # Redirect semantic paths to the entry point root (remove tags from path)
        # FIXME Normalizzare path (os.altsep => os.sep, relative => absolute)
        # /a/_b/_c/x -> dsroot/a/_b/x
        # /a/_b/_c/ -> dsroot/a/_b/_c/
        # /a/_b/_c/_d/ -> dsroot/a/_b/_d/

        components = virtualpath.split(os.sep)
        tmppath = []
        for i, name in enumerate(components):
            if i == 0 or i == 1:
                tmppath.append(name)
            else:
                if self._is_semantic_name(tmppath[i - 2]) and self._is_semantic_name(tmppath[i - 1]):
                    # _a/_b/_c => _a/_c
                    # _a/_b/x => _a/x
                    del tmppath[-1]
                tmppath.append(name)

        tmppath = os.sep.join(tmppath)
        if tmppath.startswith("/"):
            tmppath = tmppath[1:]

        path = os.path.join(self._dsroot, tmppath)

        return path

    def _full_path(self, path): # FIXME DELETEME
        return self._datastore_path(path)

    @staticmethod
    def _semantic_path_info(path) -> list:
        """

        :param path: a virtual path
        :return: [ {entrypoint: "/a/_b" (a virtual path), tags: ["_c", "_d", "_e"], file: "x" }, ... ]
        """
        info = []
        components = os.path.normpath(path).split(os.sep)
        state = 0

        for i, name in enumerate(components):

            if state == 0:
                # Searching an entry point
                if SemanticFS._is_semantic_name(name):
                    info.append({'entrypoint': os.sep.join(components[0:i + 1]), 'tags': [], 'file': ''})
                    state = 1

            elif state == 1:
                # Collecting all the tags and the final file/folder (if there is one)
                if SemanticFS._is_semantic_name(name):
                    info[-1]['tags'].append(name)
                else:
                    info[-1]['file'] = name
                    state = 0

        return info

    def _get_semantic_folder(self, path):
        # FIXME Error check: if not exists??
        storedir = self._datastore_path(path)
        graph_file = os.path.join(storedir, '$$_SEMANTIC_FS_GRAPH_FILE_$$')
        assoc_file = os.path.join(storedir, '$$_SEMANTIC_FS_ASSOC_FILE_$$')
        return SemanticFolder.from_filename(graph_file, assoc_file, path)

    def _save_semantic_folder(self, semfolder: SemanticFolder):
        storedir = self._datastore_path(semfolder.path)
        graph_file = os.path.join(storedir, '$$_SEMANTIC_FS_GRAPH_FILE_$$')
        assoc_file = os.path.join(storedir, '$$_SEMANTIC_FS_ASSOC_FILE_$$')
        semfolder.to_filename(graph_file, assoc_file)

    def _exists(self, path) -> bool:
        """

        :param path: a virtual path
        :return:
        """
        for info in self._semantic_path_info(path):
            # FIXME Potrebbe non esistere e generare un errore: in tal caso, deve restituire FALSE
            folder = self._get_semantic_folder(info['entrypoint'])
            if not (folder.graph.has_path(info['tags']) and folder.filetags.has_tags(info['file'], info['tags'])):
                return False

        return os.path.lexists(self._datastore_path(path))

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        dspath = self._datastore_path(path)
        if not os.access(dspath, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        dspath = self._datastore_path(path)
        return os.chmod(dspath, mode)

    def chown(self, path, uid, gid):
        dspath = self._datastore_path(path)
        return os.chown(dspath, uid, gid)

    def getattr(self, path, fh=None):
        print("getattr " + path)
        logger.debug("getattr(%s)", path)
        if not self._exists(path):
            logger.debug("getattr(%s): FileNotFoundError", path)
            raise FuseOSError(errno.ENOENT)

        print("aaaaaa")
        dspath = self._datastore_path(path)
        print(dspath)
        st = os.lstat(dspath)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                        'st_gid', 'st_mode', 'st_mtime',
                                                        'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        dirents = ['.', '..']
        storepath = self._datastore_path(path)

        if os.path.isdir(storepath):
            # FIXME Order??
            if SemanticFS._is_tag(path):
                pathinfo = self._semantic_path_info(path)
                folder = self._get_semantic_folder(pathinfo[-1]['entrypoint'])
                dirents.extend(folder.filetags.tagged_files(pathinfo[-1]['tags']))
            elif SemanticFS._is_entrypoint(path):
                dirents.extend(os.listdir(storepath))
            else:
                dirents.extend(os.listdir(storepath))

        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        if SemanticFS._is_tag(path):
            # Creating a new tag
            pathinfo = self._semantic_path_info(path)[-1]
            semfolder = self._get_semantic_folder(pathinfo['entrypoint'])

            if not semfolder.graph.has_node(pathinfo['tags'][-1]):
                # Create the tag dir in the entry point's root
                os.mkdir(self._datastore_path(path), mode)
                semfolder.graph.add_node(pathinfo['tags'][-1])

            if len(pathinfo['tags']) >= 2:
                semfolder.graph.add_arc(pathinfo['tags'][-2], pathinfo['tags'][-1])

            self._save_semantic_folder(semfolder)

        elif SemanticFS._is_entrypoint(path):
            # Creating a new entry point
            os.mkdir(self._datastore_path(path), mode)
            self._save_semantic_folder(SemanticFolder(path))

        elif SemanticFS._is_semantic_file(path):
            pathinfo = self._semantic_path_info(path)[-1]
            semfolder = self._get_semantic_folder(pathinfo['entrypoint'])

            if semfolder.filetags.has_file(pathinfo['file']):
                # The name already exists within the namespace
                raise FuseOSError(errno.EEXIST)
            else:
                os.mkdir(self._datastore_path(path), mode)
                semfolder.filetags.add_file(pathinfo['file'], pathinfo['tags'])
                self._save_semantic_folder(semfolder)

        else:
            # No semantic parts... do a normal mkdir
            os.mkdir(self._datastore_path(path), mode)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
                                                         'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files',
                                                         'f_flag',
                                                         'f_frsize', 'f_namemax'))

    def unlink(self, path):
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        return os.symlink(name, self._full_path(target))

    def rename(self, old, new):
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        dspath = self._datastore_path(path)
        return os.open(dspath, flags)

    def create(self, path, mode, fi=None):
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)


def main(mountpoint, root):
    FUSE(SemanticFS(root), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])
