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
        self._p = subprocess.Popen([sys.executable, '-m', 'semanticfs.fs', self._dspath, self._fspath],
                                   cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

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

    def testMkdir(self):
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

    def testGhostFile(self):
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


def main():
    unittest.main()

if __name__ == '__main__':
    main()
