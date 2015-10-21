import pickle


class Graph:

    def __init__(self):
        self._adjacency_out = {}
        self._adjacency_in = {}

    def serialize(self):
        return pickle.dumps([self._adjacency_out, self._adjacency_in])

    def deserialize(self, value):
        # FIXME Could expose to code injection: see http://docs.python.org/library/pickle.html
        data = pickle.loads(value)
        if isinstance(data, list) and data.len(data) == 2:
            self._adjacency_out, self._adjacency_in = data
        else:
            raise ValueError('Serialized data is not valid')

    def add_node(self, name):
        if name in self._adjacency_out:
            raise ValueError('Node exists')

        assert name not in self._adjacency_out
        assert name not in self._adjacency_in
        self._adjacency_out[name] = set()
        self._adjacency_in[name] = set()

    def remove_node(self, name):
        if not self.has_node(name):
            raise ValueError('Node is missing')

        assert isinstance(self._adjacency_out[name], set)
        assert isinstance(self._adjacency_in[name], set)
        del self._adjacency_out[name]
        del self._adjacency_in[name]

    def has_node(self, name) -> bool:
        assert (name in self._adjacency_out) == (name in self._adjacency_in)
        return name in self._adjacency_out

    def add_arc(self, from_node, to_node):
        if not (self.has_node(from_node) and self.has_node(to_node)):
            raise ValueError('Node is missing')

        assert isinstance(self._adjacency_out[from_node], set)
        assert isinstance(self._adjacency_in[to_node], set)
        self._adjacency_out[from_node].add(to_node)
        self._adjacency_in[to_node].add(from_node)

    def remove_arc(self, from_node, to_node):
        if not (self.has_node(from_node) and self.has_node(to_node)):
            raise ValueError('Node is missing')

        assert isinstance(self._adjacency_out[from_node], set)
        assert isinstance(self._adjacency_in[to_node], set)
        self._adjacency_out[from_node].remove(to_node)
        self._adjacency_in[to_node].remove(from_node)