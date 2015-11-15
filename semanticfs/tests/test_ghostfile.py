#!/usr/bin/env python

import unittest
import tempfile
import shutil
import os
from semanticfs.ghostfile import GhostFile


class PathInfoTests(unittest.TestCase):

    def setUp(self):
        self._dspath = tempfile.mkdtemp()
        self._datapath = os.path.join(self._dspath, "x")

    def tearDown(self):
        shutil.rmtree(self._dspath)

    def _fillfile(self, content):
        with open(self._datapath, 'wb') as f:
            f.write(content)

    def test_missing_file(self):
        self.assertRaises(FileNotFoundError, GhostFile, self._datapath, None)

    def test_empty_read(self):
        self._fillfile(b"")
        ghost = GhostFile(self._datapath, None)
        with open(self._datapath, 'rb') as f:
            self.assertEqual(ghost.read(10, 0, f.fileno()), b"")
        ghost.release()

    def test_read(self):
        self._fillfile(b"0123456789")
        ghost = GhostFile(self._datapath, None)

        with open(self._datapath, 'rb') as f:
            self.assertEqual(ghost.read(10, 0, f.fileno()), b"0123456789")
        with open(self._datapath, 'rb') as f:
            self.assertEqual(ghost.read(5, 5, f.fileno()), b"56789")
        with open(self._datapath, 'rb') as f:
            self.assertEqual(ghost.read(5, 8, f.fileno()), b"89")
        with open(self._datapath, 'rb') as f:
            self.assertEqual(ghost.read(5, 10, f.fileno()), b"")

        with open(self._datapath, 'r+b') as f:
            ghost.apply(f.fileno())
        ghost.release()

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

    def test_write_same(self):
        self._fillfile(b"0123456789")
        ghost = GhostFile(self._datapath, None)

        with open(self._datapath, 'r+b') as f:
            ghost.write(b"01234", 0, f.fileno())
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.write(b"789", 7, f.fileno())
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.write(b"345", 3, f.fileno())
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.apply(f.fileno())
        ghost.release()

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

    def test_truncate_write_same(self):
        self._fillfile(b"0123456789")
        ghost = GhostFile(self._datapath, None)

        with open(self._datapath, 'r+b') as f:
            ghost.truncate(0)
            self.assertEqual(ghost.size, 0)
            ghost.write(b"01234", 0, f.fileno())
            self.assertEqual(ghost.size, 5)
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"01234")

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.write(b"789", 7, f.fileno())
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"01234\x00\x00789")

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.write(b"345", 3, f.fileno())
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"012345\x00789")

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.apply(f.fileno())
        ghost.release()

        # Make sure the file *was* modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"012345\x00789")

    def test_truncate(self):
        self._fillfile(b"0123456789")
        ghost = GhostFile(self._datapath, None)

        with open(self._datapath, 'r+b') as f:
            ghost.truncate(0)
            self.assertEqual(ghost.size, 0)
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"")

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.apply(f.fileno())
        ghost.release()

        # Make sure the file *was* modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"")

    def test_truncate_after_eof(self):
        self._fillfile(b"0123456789")
        ghost = GhostFile(self._datapath, None)

        with open(self._datapath, 'r+b') as f:
            ghost.truncate(20)
            self.assertEqual(ghost.size, 20)
            self.assertEqual(ghost.read(100, 0, f.fileno()), b"0123456789" + b"\x00"*10)

        # Make sure the file was not modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789")

        with open(self._datapath, 'r+b') as f:
            ghost.apply(f.fileno())
        ghost.release()

        # Make sure the file *was* modified
        with open(self._datapath, 'rb') as f:
            self.assertEqual(f.read(), b"0123456789" + b"\x00"*10)


def main():
    unittest.main()

if __name__ == '__main__':
    main()
