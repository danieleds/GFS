This repository contains the code for the following paper:

"GFS: A graph-based file system enhanced with semantic features.",  
D. Di Sarli, F. Geraci,  
Proceedings of the 2017 International Conference on Information System and Data Mining.

## What is this

GFS is a semantic file system where data is organized as a graph instead of as a tree.

## Running

    pip3 install fusepy
    pip3 install intervaltree


    python3 -m semanticfs.fs /tmp/ds /tmp/fs

To launch tests:

    python3 -m unittest
