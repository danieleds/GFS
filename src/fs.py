#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno
import logging

from fuse import FUSE, FuseOSError, Operations

from semanticfolder import SemanticFolder
from pathinfo import PathInfo
from ghostfile import GhostFile

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('SemanticFSLogger')


class SemanticFS(Operations):

    SEMANTIC_FS_GRAPH_FILE_NAME = PathInfo.SEMANTIC_PREFIX + '$$_SEMANTIC_FS_GRAPH_FILE_$$'
    SEMANTIC_FS_ASSOC_FILE_NAME = PathInfo.SEMANTIC_PREFIX + '$$_SEMANTIC_FS_ASSOC_FILE_$$'

    def __init__(self, datastore_root):
        self._dsroot = datastore_root

        self._sem_writing_files = {}  # Ghostfiles for semantic files opened for write
        self._sem_writing_files_count = {}  # Count of the references for each ghostfile in self._sem_writing_files
        self._sem_write_descriptors = set()  # Opened write file descriptors for files within a semantic directory

    # Helpers
    # =======

    def _datastore_path(self, virtualpath: str) -> str:
        """
        Returns the path (of another file system) where the provided virtual object is actually stored.
        For example:
         * /a/_b/_c/x -> dsroot/a/_b/x
         * /a/_b/_c/ -> dsroot/a/_b/_c/
         * /a/_b/_c/_d/ -> dsroot/a/_b/_d/
        :param virtualpath: an absolute virtual path
        :return:
        """

        if not os.path.isabs(virtualpath):
            raise ValueError("virtualpath should be absolute")

        components = os.path.normcase(os.path.normpath(virtualpath)).split(os.sep)
        tmppath = []
        for i, name in enumerate(components):
            if i == 0 or i == 1:
                tmppath.append(name)
            else:
                if PathInfo.is_semantic_name(tmppath[-2]) and PathInfo.is_semantic_name(tmppath[-1]):
                    # _a/_b/_c => _a/_c
                    # _a/_b/x => _a/x
                    del tmppath[-1]
                tmppath.append(name)

        tmppath = os.sep.join(tmppath)

        # Remove the root from the path
        tmppath = os.path.splitdrive(tmppath)[1]
        if tmppath.startswith(os.sep):
            tmppath = tmppath[len(os.sep):]

        # Join the path with the datastore path
        path = os.path.join(self._dsroot, tmppath)

        return path

    def _add_ghost_file(self, ghost_path: str) -> GhostFile:
        """
        Adds a ghost file for the specified virtual path.
        If a ghost file already exists for that path, it doesn't add another one but keeps track
        of this additional reference (see `SemanticFS._delete_ghost_file`).
        :param ghost_path: the virtual path for the ghost file
        :return: the added GhostFile
        """
        dspath = self._datastore_path(ghost_path)
        normpath = os.path.normcase(os.path.normpath(ghost_path))

        if (dspath, normpath) in self._sem_writing_files:
            assert self._sem_writing_files_count[dspath, normpath] > 0
            self._sem_writing_files_count[dspath, normpath] += 1
        else:
            assert (dspath, normpath) not in self._sem_writing_files_count
            self._sem_writing_files[dspath, normpath] = GhostFile(dspath)
            self._sem_writing_files_count[dspath, normpath] = 1

        assert (dspath, normpath) in self._sem_writing_files and self._sem_writing_files_count[dspath, normpath] > 0
        return self._sem_writing_files[dspath, normpath]

    def _has_ghost_file(self, ghost_path: str) -> bool:
        """
        Test whether a ghost file exists for the specified path.
        :param ghost_path: the virtual path to test
        :return:
        """
        dspath = self._datastore_path(ghost_path)
        normpath = os.path.normcase(os.path.normpath(ghost_path))
        assert ((dspath, normpath) in self._sem_writing_files) == \
               ((dspath, normpath) in self._sem_writing_files_count
                and self._sem_writing_files_count[dspath, normpath] > 0)
        return (dspath, normpath) in self._sem_writing_files

    def _get_ghost_file(self, ghost_path: str) -> GhostFile:
        """
        Returns a ghost file for the specified path. If not present, raises a KeyError.
        :param ghost_path: the virtual path of the ghost file
        :return:
        """
        dspath = self._datastore_path(ghost_path)
        normpath = os.path.normcase(os.path.normpath(ghost_path))
        assert isinstance(self._sem_writing_files[dspath, normpath], GhostFile)
        return self._sem_writing_files[dspath, normpath]

    def _delete_ghost_file(self, ghost_path: str):
        """
        Deletes the ghost file for the specified path. If the reference count associated to this
        ghost path is greater than 1, it just decreases the counter (see `SemanticFS._add_ghost_file`).
        If the ghost path is not present, raises a KeyError.
        :param ghost_path: the virtual path of the ghost file
        """
        dspath = self._datastore_path(ghost_path)
        normpath = os.path.normcase(os.path.normpath(ghost_path))
        assert isinstance(self._sem_writing_files[dspath, normpath], GhostFile)
        self._sem_writing_files_count[dspath, normpath] -= 1
        assert self._sem_writing_files_count[dspath, normpath] >= 0
        if self._sem_writing_files_count[dspath, normpath] == 0:
            self._sem_writing_files[dspath, normpath].release()
            del self._sem_writing_files[dspath, normpath]
            del self._sem_writing_files_count[dspath, normpath]

    def _get_semantic_folder(self, path: str) -> SemanticFolder:
        """
        Returns a SemanticFolder object for the specified path.
        :param path: the virtual path of the entry point of the semantic folder.
        :return:
        """
        storedir = self._datastore_path(path)
        graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
        assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
        return SemanticFolder.from_filename(graph_file, assoc_file, path)

    def _save_semantic_folder(self, semfolder: SemanticFolder):
        """
        Saves the specified SemanticFolder object to the storage media.
        :param semfolder:
        """
        storedir = self._datastore_path(semfolder.path)
        graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
        assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
        semfolder.to_filename(graph_file, assoc_file)

    def _semantic_folder_loader(self, path: str) -> SemanticFolderLoader:
        return SemanticFolderLoader(self._datastore_path, path)

    def _exists(self, path: str) -> bool:
        """
        Test whether the specified virtual path exists in the file system.
        :param path: a virtual path
        :return:
        """

        # Extracts from the path all the files that belong to a semantic directory in the path.
        # E.g., given the path "/a/_b/_c/d/e/_f/g/_h", we get
        # [ '/a/_b/_c/d',
        #   '/a/_b/_c/d/e/_f/g',
        #   '/a/_b/_c/d/e/_f/g/_h' (because it's the last one and it's semantic)
        # ]
        components = os.path.normcase(os.path.normpath(path)).split(os.sep)
        semantic_endpoints = []
        prev_was_semantic = False
        for i, name in enumerate(components):
            curr_is_semantic = PathInfo.is_semantic_name(name)
            if prev_was_semantic and not curr_is_semantic:
                semantic_endpoints.append(os.sep.join(components[0:i+1]))
            prev_was_semantic = curr_is_semantic
        assert not PathInfo.is_semantic_name(components[-1]) or os.sep.join(components) not in semantic_endpoints
        if len(components) > 0 and PathInfo.is_semantic_name(components[-1]):
            semantic_endpoints.append(os.sep.join(components))

        for subpath in semantic_endpoints:
            pathinfo = PathInfo(subpath)
            assert pathinfo.is_tag or pathinfo.is_tagged_file or pathinfo.is_entrypoint

            try:
                folder = self._get_semantic_folder(pathinfo.entrypoint)
            except FileNotFoundError:
                return False

            if pathinfo.is_tagged_file and not folder.filetags.has_file(pathinfo.file):
                return False
            if not folder.graph.has_path(pathinfo.tags):
                return False
            if pathinfo.is_tagged_file and not folder.filetags.has_tags(pathinfo.file, pathinfo.tags):
                return False

        return os.path.lexists(self._datastore_path(path))

    @staticmethod
    def _is_reserved_name(name: str) -> bool:
        """
        Test whether the specified name is a reserved one for the virtual file system.
        :param name:
        :return:
        """
        lowername = os.path.normpath(os.sep + name.lower())
        return lowername.endswith(os.sep + SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME.lower()) \
               or lowername.endswith(os.sep + SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME.lower())

    @staticmethod
    def _stringify_open_flags(flags):
        names = ["O_RDONLY", "O_WRONLY", "O_RDWR", "O_APPEND", "O_CREAT",
                 "O_EXCL", "O_TRUNC", "O_DSYNC", "O_RSYNC", "O_SYNC",
                 "O_NDELAY", "O_NONBLOCK", "O_NOCTTY", "O_SHLOCK", "O_EXLOCK",
                 "O_BINARY", "O_NOINHERIT", "O_SHORT_LIVED", "O_TEMPORARY",
                 "O_RANDOM", "O_SEQUENTIAL", "O_TEXT", "O_ASYNC", "O_DIRECT",
                 "O_DIRECTORY", "O_NOFOLLOW", "O_NOATIME" ]

        active_flags = []

        for name in names:
            if hasattr(os, name) and flags & getattr(os, name) != 0:
                active_flags.append(name)

        if not active_flags:
            active_flags.append(names[0])

        return "|".join(active_flags)

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

        attribs = dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                           'st_gid', 'st_mode', 'st_mtime',
                                                           'st_nlink', 'st_size', 'st_uid'))

        if self._has_ghost_file(path):
            attribs['st_size'] = self._get_ghost_file(path).size

        return attribs

    def readdir(self, path: str, fh):
        """
        Yelds the list of files and directories within the provided one.
        Already traversed tags of a semantic directory are not shown.
        :param path:
        :param fh:
        """
        dirents = []
        storepath = self._datastore_path(path)

        if os.path.isdir(storepath):
            pathinfo = PathInfo(path)
            if pathinfo.is_tag:
                folder = self._get_semantic_folder(pathinfo.entrypoint)
                # Show tags first
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
        # TODO
        pathname = os.readlink(self._datastore_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self._dsroot)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        # TODO
        return os.mknod(self._datastore_path(path), mode, dev)

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
            - if path points to a folder directly under the entry point,
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
                # Removing the tag in the entry point's root
                os.rmdir(self._datastore_path(path))
                semfolder.graph.remove_node(pathinfo.tags[-1])
            else:
                semfolder.graph.remove_arc(pathinfo.tags[-2], pathinfo.tags[-1])

            self._save_semantic_folder(semfolder)

        elif pathinfo.is_entrypoint:
            dspath = self._datastore_path(path)

            # Even if the dir is logically empty, we can't remove it from the datastore because it contains
            # some special files. So first we make sure that the dir is empty from the user point-of-view, then
            # we unlink the special files, and at last we remove the directory.
            files = os.listdir(dspath)
            fsfiles = [SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME]
            if set(files).issubset(fsfiles):
                for f in fsfiles:
                    os.unlink(os.path.join(dspath, f))
                os.rmdir(dspath)
            else:
                raise FuseOSError(errno.ENOTEMPTY)

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

            self._save_semantic_folder(semfolder)

        else:
            os.rmdir(self._datastore_path(path))

    def mkdir(self, path, mode):
        """
         * Standard directory: standard behavior
         * Entry point: creates the specified directory and adds the
           necessary metadata.
         * Tag:
            - if path points to a tag directly under the entry point, it adds the folder
              to the entry point and adds the relative node to the graph. Fails if the
              tag did exist.
            - if path points to a tag contained within another tag, it adds a link in the
              graph from the containing tag to the new one (if the tag that is being
              added didn't already exist within the semantic directory, it first adds the
              node to the graph and the tag folder to the entry point).
              Fails if the specified tag (associated to this semantic folder) is already
              present within the destination path. In other words, a tag can't be added
              if it has already been traversed.
         * Tagged folder: create the folder directly under the entry point, and add
              the appropriate tags. If the folder already exists under the entry point,
              just add the tags.
        :param path:
        :param mode:
        :raise FuseOSError:
        """
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
                semfolder.filetags.assign_tags(pathinfo.file, pathinfo.tags)
            else:
                os.mkdir(self._datastore_path(path), mode)
                semfolder.filetags.add_file(pathinfo.file, pathinfo.tags)
            self._save_semantic_folder(semfolder)

        else:
            # No semantic parts... do a normal mkdir
            os.mkdir(self._datastore_path(path), mode)

    def statfs(self, path):
        storepath = self._datastore_path(path)
        stv = os.statvfs(storepath)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
                                                         'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files',
                                                         'f_flag',
                                                         'f_frsize', 'f_namemax'))

    def unlink(self, path):
        """
         * Standard file: standard behavior
         * Tagged file:
            - if path points to a file directly under the entry poiny,
              it completely deletes the file.
            - if path points to a file with one or more tags, remove
              from the file the last tag in the path.
        :param path:
        :return:
        """
        pathinfo = PathInfo(path)
        if pathinfo.is_tag or pathinfo.is_entrypoint:
            raise FuseOSError(errno.EISDIR)

        elif pathinfo.is_tagged_file:
            semfolder = self._get_semantic_folder(pathinfo.entrypoint)
            assert len(pathinfo.file) > 0

            if len(pathinfo.tags) == 0:
                # If it's directly under the entry point, delete it.
                os.unlink(self._datastore_path(path))
                semfolder.filetags.remove_file(pathinfo.file)
            else:
                # If it's a tagged path, remove the last tag.
                semfolder.filetags.discard_tag(pathinfo.file, pathinfo.tags[-1])

            self._save_semantic_folder(semfolder)

        else:
            os.unlink(self._datastore_path(path))

    def symlink(self, name, target):
        # TODO
        return os.symlink(name, self._datastore_path(target))

    def rename(self, old, new):
        # TODO
        pathinfo_old = PathInfo(old)
        pathinfo_new = PathInfo(new)

        # FIXME Dest is empty? Old = new?

        if pathinfo_old.is_tagged_file and pathinfo_new.is_tagged_file \
                and pathinfo_old.entrypoint == pathinfo_new.entrypoint:

            # Moving a file within the same entry point.

            # Moving over itself. This case should have already been prevented by FUSE!
            assert not (pathinfo_old.file == pathinfo_new.file and set(pathinfo_old.tags) == set(pathinfo_new.tags))

            if pathinfo_old.file != pathinfo_new.file \
                    and set(pathinfo_old.tags) == set(pathinfo_new.tags):

                # These cases:
                #  * mv /_sem/_t1/x /_sem/_t1/y
                #  * mv /_sem/x /_sem/y

                # Rename the file in the root and in filestagsassociations
                assert pathinfo_old.file != "" and pathinfo_new.file != ""
                os.rename(self._datastore_path(old), self._datastore_path(new))
                semfolder = self._get_semantic_folder(pathinfo_new.entrypoint)
                semfolder.filetags.rename_file(pathinfo_old.file, pathinfo_new.file)
                self._save_semantic_folder(semfolder)

            elif pathinfo_old.file != pathinfo_new.file \
                    and set(pathinfo_old.tags) != set(pathinfo_new.tags):

                # mv /_sem/_t1/x /_sem/_t2/y is not supported
                raise FuseOSError(errno.ENOTSUP)

            elif pathinfo_old.file == pathinfo_new.file \
                    and set(pathinfo_old.tags) != set(pathinfo_new.tags):

                # These cases:
                #  * mv /_sem/_t1/x /_sem/_t2/x
                #  * mv /_sem/x /_sem/_t3/x
                with self._semantic_folder_loader(pathinfo_new.entrypoint) as semfolder:
                    # semfolder = self._get_semantic_folder(pathinfo_new.entrypoint)
                    if len(pathinfo_old.tags) > 0:
                        semfolder.filetags.discard_tag(pathinfo_old.tags[-1])
                    semfolder.filetags.assign_tags(pathinfo_new.tags)
                    # self._save_semantic_folder(semfolder)

        else:
            pass

    def link(self, target, name):
        # TODO
        return os.link(self._datastore_path(target), self._datastore_path(name))

    def utimens(self, path, times=None):
        # TODO
        return os.utime(self._datastore_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        dspath = self._datastore_path(path)
        f = os.open(dspath, flags)
        logger.debug("open(%s, %s) -> %d", path, SemanticFS._stringify_open_flags(flags), f)

        if flags & (os.O_WRONLY | os.O_RDWR) != 0:
            pathinfo = PathInfo(path)
            if pathinfo.is_tagged_file:
                # FIXME What if path == dspath??? Maybe already works, just check.
                assert f not in self._sem_write_descriptors
                self._sem_write_descriptors.add(f)
                self._add_ghost_file(path)

        return f

    def create(self, path, mode, fi=None):
        """
         * Standard file: standard behavior
         * Tagged file: create the file directly under the entry point, and add
           the appropriate tags. If the file already exists under the entry point,
           just add the tags.
        :param path:
        :param mode:
        :param fi:
        :return: write descriptor for the file
        """
        pathinfo = PathInfo(path)
        dspath = self._datastore_path(path)
        f = os.open(dspath, os.O_WRONLY | os.O_CREAT, mode)
        logger.debug("create(%s, %s) -> %d", path, SemanticFS._stringify_open_flags(os.O_WRONLY | os.O_CREAT), f)


        if pathinfo.is_tagged_file:
            # FIXME What if path == dspath??? Maybe already works, just check.

            assert f not in self._sem_write_descriptors
            self._sem_write_descriptors.add(f)
            self._add_ghost_file(path).truncate(0)

            semfolder = self._get_semantic_folder(pathinfo.entrypoint)
            if semfolder.filetags.has_file(pathinfo.file):
                semfolder.filetags.assign_tags(pathinfo.file, pathinfo.tags)
            else:
                semfolder.filetags.add_file(pathinfo.file, pathinfo.tags)
            self._save_semantic_folder(semfolder)

            assert self._has_ghost_file(path)

        return f

    def read(self, path, length, offset, fh):
        if self._has_ghost_file(path):
            return self._get_ghost_file(path).read(length, offset, fh)
        else:
            os.lseek(fh, offset, os.SEEK_SET)
            return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        if self._has_ghost_file(path):
            return self._get_ghost_file(path).write(buf, offset, fh)
        else:
            os.lseek(fh, offset, os.SEEK_SET)
            return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        logger.debug("truncate(%s, %d)", path, length)
        if self._has_ghost_file(path):
            self._get_ghost_file(path).truncate(length)
        else:
            dspath = self._datastore_path(path)
            with open(dspath, 'r+') as f:
                f.truncate(length)

    def flush(self, path, fh):
        # TODO
        return os.fsync(fh)

    def release(self, path, fh):
        logger.debug("close(%s, %d)", path, fh)
        if fh in self._sem_write_descriptors:
            assert self._has_ghost_file(path) and PathInfo(path).is_tagged_file
            self._get_ghost_file(path).apply(fh)
            self._delete_ghost_file(path)
            self._sem_write_descriptors.remove(fh)

        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        # TODO
        return self.flush(path, fh)


class SemanticFolderLoader:

    def __init__(self, path_conversion_fun, virtual_path):
        self._path_conversion_fun = path_conversion_fun
        self._path = virtual_path

    def __enter__(self):
        storedir = self._path_conversion_fun(self._path)
        graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
        assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
        return SemanticFolder.from_filename(graph_file, assoc_file, self._path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert exc_type is SemanticFolder
        # Save semfolder to disk
        storedir = self._path_conversion_fun(self._path)
        graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
        assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
        exc_val.to_filename(graph_file, assoc_file)


def main(mountpoint, root):
    FUSE(SemanticFS(root), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])
