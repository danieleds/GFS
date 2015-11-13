#!/usr/bin/env python

import tempfile
import shutil
import os
import logging
import signal
import unittest
import subprocess
import sys

logging.basicConfig()
logging.getLogger('SemanticFSLogger').setLevel(logging.FATAL)


class FunctionalTests(unittest.TestCase):

    def setUp(self):
        self._dspath = tempfile.mkdtemp()
        self._fspath = tempfile.mkdtemp()
        cwd = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + os.sep + ".." + os.sep + "..")
        self._p = subprocess.Popen([sys.executable, '-m', 'semanticfs.fs', self._dspath, self._fspath], cwd=cwd)

    def tearDown(self):
        os.kill(self._p.pid, signal.SIGINT)
        shutil.rmtree(self._dspath)
        shutil.rmtree(self._fspath)

    def testMkdir(self):
        os.mkdir(os.path.join(self._fspath, 'standardDir'))
        os.mkdir(os.path.join(self._fspath, '_semanticDir'))

        try:
            os.mkdir(os.path.join(self._fspath, 'standardDir'))
        except FileExistsError:
            pass

        try:
            os.mkdir(os.path.join(self._fspath, '_semanticDir'))
        except FileExistsError:
            pass


def main():
    unittest.main()

if __name__ == '__main__':
    main()
