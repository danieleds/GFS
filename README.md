This repository contains the code for the following paper:

["GFS: A graph-based file system enhanced with semantic features."](https://www-old.iit.cnr.it/sites/default/files/gfs.pdf),  
D. Di Sarli, F. Geraci,  
Proceedings of the 2017 International Conference on Information System and Data Mining.

## What is this

Organizing documents in the file system is one of the most tedious and thorny tasks for most computer users. Taxonomies based on hand made directory hierarchies still remain the only possible alternative for most small and medium enterprises, public administrations and individual users. However, both the limitations of the hierarchical organization of filesystems and the difficulty of maintaining the coherence within the taxonomy have raised the need for more scalable and effective approaches.

Desktop searching applications provide proprietary interfaces that enable content-based searching at the cost of having no control on the indexing and ranking of results. Semantic file systems, instead, leave users the freedom to manage the taxonomy according to their specific needs, but lose the standard file system features.

GFS (graph-based file system) is a new hybrid file system that extends the standard hierarchical organization of files with semantic features. GFS allows the user to nest semantic spaces inside the directory hierarchy leaving unaltered system folders. Semantic spaces allow customized file tagging and leverage on browsing to guide file searching.

Since GFS does not change the low-level interface to interact with file systems, users can continue to use their favorite file managers to interact with it. Moreover, no changes are required to integrate the semantic features in proprietary software.

## Running

    pip3 install fusepy
    pip3 install intervaltree


    python3 -m semanticfs.fs /tmp/ds /tmp/fs

To launch tests:

    python3 -m unittest
