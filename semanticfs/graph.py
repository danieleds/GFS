import pickle
import itertools


class Graph:

    def __init__(self):
        self._adjacency_out = {}
        self._adjacency_in = {}

    def serialize(self):
        return pickle.dumps([self._adjacency_out, self._adjacency_in])

    def deserialize(self, value):
        # FIXME Could expose to code injection: see http://docs.python.org/library/pickle.html
        data = pickle.loads(value)
        if isinstance(data, list) and len(data) == 2:
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

    def rename_node(self, old, new):
        if not self.has_node(old):
            raise ValueError('Node is missing')

        if self.has_node(new):
            raise ValueError('Node name already exists')

        self._adjacency_in[new] = self._adjacency_in.pop(old)
        self._adjacency_out[new] = self._adjacency_out.pop(old)
        for key, nodes in itertools.chain(self._adjacency_in.items(), self._adjacency_out.items()):
            assert isinstance(nodes, set)
            nodes.discard(old)
            nodes.add(new)

    def has_node(self, name) -> bool:
        assert (name in self._adjacency_out) == (name in self._adjacency_in)
        return name in self._adjacency_out

    def nodes(self):
        return self._adjacency_in.keys()

    def has_arc(self, from_node, to_node) -> bool:
        assert (to_node in self._adjacency_out[from_node]) == (from_node in self._adjacency_in[to_node])
        return to_node in self._adjacency_out[from_node]

    def has_path(self, nodes) -> bool:
        for i, node in enumerate(nodes):
            if self.has_node(node):
                if i == 0:
                    continue
                elif not self.has_arc(nodes[i-1], node):
                    return False
            else:
                return False
        return True

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

    def incoming_arcs(self, node) -> list:
        # FIXME Is this method (and self._adjacency_in) really necessary?
        if not self.has_node(node):
            raise ValueError('Node is missing')

        return self._adjacency_in[node]

    def outgoing_arcs(self, node) -> list:
        if not self.has_node(node):
            raise ValueError('Node is missing')

        return self._adjacency_out[node]
