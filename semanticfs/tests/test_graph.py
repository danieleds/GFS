#!/usr/bin/env python

import unittest
from semanticfs.graph import Graph


class PathInfoTests(unittest.TestCase):

    def test_remove_node(self):
        g = Graph()
        g.add_node("a")
        g.add_node("b")
        g.add_arc("a", "b")
        g.add_arc("b", "a")

        self.assertTrue(g.has_arc("a", "b"))
        self.assertTrue(g.has_arc("b", "a"))

        g.remove_node("a")
        g.add_node("a")

        self.assertFalse(g.has_arc("a", "b"))
        self.assertFalse(g.has_arc("b", "a"))


def main():
    unittest.main()

if __name__ == '__main__':
    main()
