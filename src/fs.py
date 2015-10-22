#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno
import logging

from fuse import FUSE, FuseOSError, Operations

from semanticfolder import SemanticFolder
from pathinfo import PathInfo

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('SemanticFSLogger')


class SemanticFS(Operations):

    SEMANTIC_FS_GRAPH_FILE_NAME = PathInfo.SEMANTIC_PREFIX + '$$_SEMANTIC_FS_GRAPH_FILE_$$'
    SEMANTIC_FS_ASSOC_FILE_NAME = PathInfo.SEMANTIC_PREFIX + '$$_SEMANTIC_FS_ASSOC_FILE_$$'

    def __init__(self, datastore_root):
        self._dsroot = datastore_root
        # self.root = datastore_root

    # Helpers
    # =======

    def _datastore_path(self, virtualpath) -> str:
        """
        Returns the path (of another file system) where the provided virtual object is actually stored.
        For example:
         * /a/_b/_c/x -> dsroot/a/_b/x
         * /a/_b/_c/ -> dsroot/a/_b/_c/
         * /a/_b/_c/_d/ -> dsroot/a/_b/_d/
        :param virtualpath:
        :return:
        """
        components = os.path.normpath(virtualpath).split(os.sep)
        tmppath = []
        for i, name in enumerate(components):
            if i == 0 or i == 1:
                tmppath.append(name)
            else:
                if PathInfo.is_semantic_name(tmppath[i - 2]) and PathInfo.is_semantic_name(tmppath[i - 1]):
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
                if PathInfo.is_semantic_name(name):
                    info.append({'entrypoint': os.sep.join(components[0:i + 1]), 'tags': [], 'file': ''})
                    state = 1

            elif state == 1:
                # Collecting all the tags and the final file/folder (if there is one)
                if PathInfo.is_semantic_name(name):
                    info[-1]['tags'].append(name)
                else:
                    info[-1]['file'] = name
                    state = 0

        return info

    def _get_semantic_folder(self, path):
        # FIXME Error check: if not exists??
        storedir = self._datastore_path(path)
        graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
        assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
        return SemanticFolder.from_filename(graph_file, assoc_file, path)

    def _save_semantic_folder(self, semfolder: SemanticFolder):
        storedir = self._datastore_path(semfolder.path)
        graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
        assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
        semfolder.to_filename(graph_file, assoc_file)

    def _exists(self, path) -> bool:
        """

        :param path: a virtual path
        :return:
        """
        for info in self._semantic_path_info(path):
            # FIXME Potrebbe non esistere e generare un errore: in tal caso, deve restituire FALSE
            folder = self._get_semantic_folder(info['entrypoint'])
            if info['file'] != '' and not folder.filetags.has_file(info['file']):
                return False
            if not folder.graph.has_path(info['tags']):
                return False
            if info['file'] != '' and not folder.filetags.has_tags(info['file'], info['tags']):
                return False

        return os.path.lexists(self._datastore_path(path))

    @staticmethod
    def _is_reserved_name(name) -> bool:
        lowername = os.path.normpath(os.sep + name.lower())
        return lowername.endswith(os.sep + SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME.lower()) \
               or lowername.endswith(os.sep + SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME.lower())

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        logger.debug("access(%s)", path)
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
        if SemanticFS._is_reserved_name(path):
            raise FuseOSError(errno.EINVAL)

        if not self._exists(path):
            raise FuseOSError(errno.ENOENT)

        dspath = self._datastore_path(path)
        st = os.lstat(dspath)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                        'st_gid', 'st_mode', 'st_mtime',
                                                        'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        dirents = []
        storepath = self._datastore_path(path)

        if os.path.isdir(storepath):
            # FIXME Order??
            pathinfo = PathInfo(path)
            if pathinfo.is_tag:
                folder = self._get_semantic_folder(pathinfo.entrypoint)
                dirents.extend(folder.graph.outgoing_arcs(pathinfo.tags[-1]))
                dirents.extend(folder.filetags.tagged_files(pathinfo.tags))
            elif pathinfo.is_entrypoint:
                dirents.extend(os.listdir(storepath))
            else:
                dirents.extend(os.listdir(storepath))

            # Remove reserved names and already traversed tags
            dirents = [x for x in dirents if not SemanticFS._is_reserved_name(x)
                       and x not in pathinfo.tags]

        for r in ['.', '..'] + dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self._dsroot)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        """
         * Standard directory: standard behavior
         * Entry point: standard behavior
         * Tag:
            - if path points to a tag directly under the entry point,
              it completely deletes the tag. Fails if tag is not empty.
            - if path points to a tag contained within another tag,
              it removes the corresponding link in the graph. Doesn't
              fail if the tag is not empty.
         * Tagged folder:
            - if path points to a folder directly under the entry poiny,
              it completely deletes the folder. Fails if the folder is not
              empty, as would do the standard os call.
            - if path points to a folder with one or more tags, remove
              from the folder the last tag in the path. Doesn't fail if
              the folder is not empty.
        :param path:
        :return:
        """
        pathinfo = PathInfo(path)
        if pathinfo.is_tag:
            semfolder = self._get_semantic_folder(pathinfo.entrypoint)
            assert len(pathinfo.tags) >= 1

            if len(pathinfo.tags) == 1:
                os.rmdir(self._datastore_path(path))
                semfolder.graph.remove_node(pathinfo.tags[-1])
            else:
                semfolder.graph.remove_arc(pathinfo.tags[-2], pathinfo.tags[-1])

        elif pathinfo.is_entrypoint:
            os.rmdir(self._datastore_path(path))

        elif pathinfo.is_tagged_file:
            semfolder = self._get_semantic_folder(pathinfo.entrypoint)
            assert len(pathinfo.file) > 0

            if len(pathinfo.tags) == 0:
                # If it's directly under the entry point, delete it.
                os.rmdir(self._datastore_path(path)) # Raises error if dir is not empty
                semfolder.filetags.remove_file(pathinfo.file)
            else:
                # If it's a tagged path, remove the last tag.
                semfolder.filetags.discard_tag(pathinfo.file, pathinfo.tags[-1])

        else:
            os.rmdir(self._datastore_path(path))

    def mkdir(self, path, mode):
        pathinfo = PathInfo(path)
        if pathinfo.is_tag:
            # Creating a new tag
            if pathinfo.tags[-1] in pathinfo.tags[0:-1]:
                raise FuseOSError(errno.EEXIST)

            logger.debug("Creating tag: %s", path)
            semfolder = self._get_semantic_folder(pathinfo.entrypoint)

            if not semfolder.graph.has_node(pathinfo.tags[-1]):
                # Create the tag dir in the entry point's root
                os.mkdir(self._datastore_path(path), mode)
                semfolder.graph.add_node(pathinfo.tags[-1])

            if len(pathinfo.tags) >= 2:
                semfolder.graph.add_arc(pathinfo.tags[-2], pathinfo.tags[-1])

            self._save_semantic_folder(semfolder)

        elif pathinfo.is_entrypoint:
            # Creating a new entry point
            logger.debug("Creating entry point: %s", path)
            os.mkdir(self._datastore_path(path), mode)
            self._save_semantic_folder(SemanticFolder(path))

        elif pathinfo.is_tagged_file:
            # Adding a standard folder to a semantic directory
            logger.debug("Adding standard folder to semantic dir: %s", path)
            semfolder = self._get_semantic_folder(pathinfo.entrypoint)

            if semfolder.filetags.has_file(pathinfo.file):
                # The name already exists within the namespace
                raise FuseOSError(errno.EEXIST)
            else:
                os.mkdir(self._datastore_path(path), mode)
                semfolder.filetags.add_file(pathinfo.file, pathinfo.tags)
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
