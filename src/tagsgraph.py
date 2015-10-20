class TagsGraph:
    
    adjacency_out = {}
    adjacency_in = {}
    
    def __init__(self):
        pass
    
    def serialize(self):
        pass
        
    def deserialize(self):
        pass
        
    def add_node(self, name):
        if name in self.adjacency_out:
            raise ValueError('Node exists')

        self.adjacency_out[name] = set()
        self.adjacency_in[name] = set()

    def remove_node(self, name):
        if not self.has_node(name):
            raise ValueError('Node is missing')

        del self.adjacency_out[name]
        del self.adjacency_in[name]

    def has_node(self, name) -> bool:
        return name in self.adjacency_out
        
    def add_arc(self, from_node, to_node):
        if not (self.has_node(from_node) and self.has_node(to_node)):
            raise ValueError('Node is missing')

        assert isinstance(self.adjacency_out[from_node], set)
        assert isinstance(self.adjacency_in[to_node], set)
        self.adjacency_out[from_node].add(to_node)
        self.adjacency_in[to_node].add(from_node)
        
    def remove_arc(self, from_node, to_node):
        if not (self.has_node(from_node) and self.has_node(to_node)):
            raise ValueError('Node is missing')

        assert isinstance(self.adjacency_out[from_node], set)
        assert isinstance(self.adjacency_in[to_node], set)
        self.adjacency_out[from_node].remove(to_node)
        self.adjacency_in[to_node].remove(from_node)
