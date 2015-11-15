#!/usr/bin/env python

import tempfile
import shutil
import os
import signal
import unittest
import subprocess
import sys
import time


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        self._dspath = tempfile.mkdtemp()
        self._fspath = tempfile.mkdtemp()
        cwd = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
        show_output = False
        self._p = subprocess.Popen([sys.executable, '-m', 'semanticfs.fs', self._dspath, self._fspath],
                                   cwd=cwd,
                                   stdout=None if show_output else subprocess.DEVNULL,
                                   stderr=subprocess.STDOUT)

        # Wait until file system starts
        while not os.path.ismount(self._fspath):
            time.sleep(0.1)

    def tearDown(self):
        os.kill(self._p.pid, signal.SIGINT)
        self._p.wait()
        shutil.rmtree(self._dspath)
        shutil.rmtree(self._fspath)

    def _path(self, *paths):
        return os.path.join(self._fspath, *paths)

    def test_mkdir(self):
        os.mkdir(self._path('standardDir'))
        os.mkdir(self._path('_semanticDir'))
        os.mkdir(self._path('_semanticDir', '_tag1'))
        os.mkdir(self._path('_semanticDir', '_tag1', 'taggedDir'))

        self.assertRaises(FileExistsError, os.mkdir, self._path('standardDir'))
        self.assertRaises(FileExistsError, os.mkdir, self._path('_semanticDir'))
        self.assertRaises(FileExistsError, os.mkdir, self._path('_semanticDir', '_tag1'))
        self.assertRaises(FileExistsError, os.mkdir, self._path('_semanticDir', '_tag1', 'taggedDir'))

        os.mkdir(self._path('_semanticDir', '_tag1', '_tag2'))
        self.assertTrue(os.path.exists(self._path('_semanticDir', '_tag2')))

        self.assertRaises(FileExistsError, os.mkdir, self._path('_semanticDir', '_tag1', '_tag2', '_tag1'))

    def test_ghost_file_copy(self):
        os.mkdir(self._path('_sem'))
        os.mkdir(self._path('_sem', '_t1'))
        os.mkdir(self._path('_sem', '_t2'))

        goldcontent = b"HelloWorld" * 100000  # 1000kB

        with open(self._path('_sem', 'x'), 'wb') as f:
            f.write(goldcontent)

        shutil.copy2(self._path('_sem', 'x'), self._path('_sem', '_t1', 'x'))

        with open(self._path('_sem', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent)

        shutil.copy2(self._path('_sem', 'x'), self._path('_sem', '_t1', 'x'))

        with open(self._path('_sem', '_t1', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent)

        shutil.copy2(self._path('_sem', '_t1', 'x'), self._path('_sem', '_t2', 'x'))

        with open(self._path('_sem', '_t2', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent)

        shutil.copy2(self._path('_sem', '_t1', 'x'), self._path('_sem', 'x'))

        with open(self._path('_sem', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent)

    def test_ghost_file_truncate(self):
        os.mkdir(self._path('_sem'))
        os.mkdir(self._path('_sem', '_t1'))

        goldcontent = b"abcdefghijklmnopqrstuvwxyz"

        with open(self._path('_sem', 'x'), 'wb') as f:
            f.write(goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'wb'):

            with open(self._path('_sem', 'x'), 'rb') as f_x:
                self.assertEqual(f_x.read(), goldcontent)

            with open(self._path('_sem', '_t1', 'x'), 'rb') as f_t1_rx:
                self.assertEqual(len(f_t1_rx.read()), 0)

    def test_ghost_file_different_write(self):
        os.mkdir(self._path('_sem'))
        os.mkdir(self._path('_sem', '_t1'))

        goldcontent = b"abcdefghijklmnopqrstuvwxyz"

        with open(self._path('_sem', 'x'), 'wb') as f:
            f.write(goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'wb') as f_t1_x:
            f_t1_x.write(b"!!!" + goldcontent)
            f_t1_x.flush()

            with open(self._path('_sem', 'x'), 'rb') as f_x:
                self.assertEqual(f_x.read(), b"!!!" + goldcontent)

            with open(self._path('_sem', '_t1', 'x'), 'rb') as f_t1_rx:
                self.assertEqual(f_t1_rx.read(), b"!!!" + goldcontent)

        with open(self._path('_sem', 'x'), 'rb') as f:
            self.assertEqual(f.read(), b"!!!" + goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'rb') as f:
            self.assertEqual(f.read(), b"!!!" + goldcontent)

    def test_ghost_file_truncate2(self):
        os.mkdir(self._path('_sem'))
        os.mkdir(self._path('_sem', '_t1'))

        goldcontent = b"abcdefghijklmnopqrstuvwxyz"

        with open(self._path('_sem', 'x'), 'wb') as f:
            f.write(goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'wb') as f_t1_x:
            f_t1_x.write(goldcontent)
            f_t1_x.flush()
            f_t1_x.truncate(10)

            with open(self._path('_sem', 'x'), 'rb') as f_x:
                self.assertEqual(f_x.read(), goldcontent)

            with open(self._path('_sem', '_t1', 'x'), 'rb') as f_t1_rx:
                self.assertEqual(f_t1_rx.read(), goldcontent[0:10])

        # Clear stat cache
        os.chmod(self._path('_sem', 'x'), os.lstat(self._path('_sem', 'x')).st_mode)

        self.assertEqual(os.path.getsize(self._path('_sem', 'x')), 10)
        self.assertEqual(os.path.getsize(self._path('_sem', '_t1', 'x')), 10)

        with open(self._path('_sem', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent[0:10])

        with open(self._path('_sem', '_t1', 'x'), 'rb') as f:
            self.assertEqual(f.read(), goldcontent[0:10])

    def test_ghost_file_seek_writes(self):
        os.mkdir(self._path('_sem'))
        os.mkdir(self._path('_sem', '_t1'))

        goldcontent = b"abcdefghijklmnopqrstuvwxyz"

        with open(self._path('_sem', 'x'), 'wb') as f:
            f.write(goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'wb') as f_w:

            with open(self._path('_sem', 'x'), 'rb') as f_r:
                self.assertEqual(f_r.read(), goldcontent)

            f_w.seek(5)
            f_w.write(b"fghi")
            f_w.flush()

            with open(self._path('_sem', 'x'), 'rb') as f_r:
                self.assertEqual(f_r.read(), goldcontent)
            with open(self._path('_sem', '_t1', 'x'), 'rb') as f_r:
                self.assertEqual(f_r.read(), b"\x00"*5 + b"fghi")

    def test_ghost_file_seek_writes2(self):
        os.mkdir(self._path('_sem'))
        os.mkdir(self._path('_sem', '_t1'))

        goldcontent = b"abcdefghijklmnopqrstuvwxyz"

        with open(self._path('_sem', 'x'), 'wb') as f:
            f.write(goldcontent)

        with open(self._path('_sem', '_t1', 'x'), 'wb') as f_w:

            with open(self._path('_sem', 'x'), 'rb') as f_r:
                self.assertEqual(f_r.read(), goldcontent)

            f_w.seek(5)
            f_w.write(b"5555")
            f_w.flush()

            # Clear stat cache
            os.chmod(self._path('_sem', 'x'), os.lstat(self._path('_sem', 'x')).st_mode)

            with open(self._path('_sem', 'x'), 'rb') as f_r:
                self.assertEqual(f_r.read(), b"\x00"*5 + b"5555")
            with open(self._path('_sem', '_t1', 'x'), 'rb') as f_r:
                self.assertEqual(f_r.read(), b"\x00"*5 + b"5555")

        with open(self._path('_sem', 'x'), 'rb') as f_r:
            self.assertEqual(f_r.read(), b"\x00"*5 + b"5555")
        with open(self._path('_sem', '_t1', 'x'), 'rb') as f_r:
            self.assertEqual(f_r.read(), b"\x00"*5 + b"5555")


def main():
    unittest.main()

if __name__ == '__main__':
    main()
