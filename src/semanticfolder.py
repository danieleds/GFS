from graph import Graph
from filestagsassociation import FilesTagsAssociation


class SemanticFolder(object):

    def __init__(self, path, graph=None, filetags=None):
        self.__path = path

        if graph is None:
            self.graph = Graph()
        else:
            self.graph = graph

        if filetags is None:
            self.filetags = FilesTagsAssociation()
        else:
            self.filetags = filetags

    @property
    def path(self):
        return self.__path

    @classmethod
    def from_filename(cls, graph_file, assoc_file, path):
        """
        Given two files (handled by another file system) containing the relevant data,
        constructs a SemanticFolder object.
        :param graph_file: the path of the Graph file
        :param assoc_file: the path of the FilesTagsAssociation file
        :param path: the virtual path of this semantic folder
        :return:
        """
        graph = Graph()
        with open(graph_file, 'r') as f:
            graph.deserialize(f.read())

        filetags = FilesTagsAssociation()
        with open(assoc_file, 'r') as f:
            filetags.deserialize(f.read())

        # FIXME Cache it
        return cls(path, graph, filetags)
