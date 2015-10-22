import sys
import os

from fs import SemanticFS
from semanticfolder import SemanticFolder


def main(operation, path):
    if operation == 'info':
        folder = _get_semantic_folder(path)
        print('Files:')
        for file in folder.filetags.files():
            print(file + ' --> ' + str(folder.filetags.tags(file)))


def _get_semantic_folder(path):
    storedir = path
    graph_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_GRAPH_FILE_NAME)
    assoc_file = os.path.join(storedir, SemanticFS.SEMANTIC_FS_ASSOC_FILE_NAME)
    return SemanticFolder.from_filename(graph_file, assoc_file, path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
