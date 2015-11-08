#!/usr/bin/env python

import threading
import tempfile
import time
import shutil
import os
import logging
import signal

from semanticfs import fs

logging.basicConfig()
logging.getLogger('SemanticFSLogger').setLevel(logging.FATAL)


def tests_thread(dspath, fspath):
    time.sleep(1)

    # Create directory
    os.mkdir(os.path.join(fspath, 'folder'))
    print(".", end='')
    os.mkdir(os.path.join(fspath, '_semfolder'))
    print(".", end='')

    print("\nDone")
    os.kill(os.getpid(), signal.SIGINT)


def start():
    # main(sys.argv[2], sys.argv[1])
    try:
        dspath = tempfile.mkdtemp()
        fspath = tempfile.mkdtemp()

        t = threading.Thread(target=tests_thread, args=(dspath, fspath))
        t.daemon = True
        t.start()

        fs.start(fspath, dspath)

    finally:
        shutil.rmtree(dspath)
        shutil.rmtree(fspath)

