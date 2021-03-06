from .graph import Graph
from .filestagsassociation import FilesTagsAssociation


class SemanticFolder:

    def __init__(self, path, graph=None, filetags=None):
        self.__path = path

        if graph is None:
            self.__graph = Graph()
        else:
            self.__graph = graph

        if filetags is None:
            self.__filetags = FilesTagsAssociation()
        else:
            self.__filetags = filetags

    @property
    def path(self):
        return self.__path

    @property
    def graph(self) -> Graph:
        return self.__graph

    @property
    def filetags(self) -> FilesTagsAssociation:
        return self.__filetags

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
        with open(graph_file, 'rb') as f:
            graph.deserialize(f.read())

        filetags = FilesTagsAssociation()
        with open(assoc_file, 'rb') as f:
            filetags.deserialize(f.read())

        # TODO Cache it
        return cls(path, graph, filetags)

    def to_filename(self, graph_file, assoc_file):
        with open(graph_file, 'wb') as f:
            f.write(self.graph.serialize())

        with open(assoc_file, 'wb') as f:
            f.write(self.filetags.serialize())
