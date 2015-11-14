#!/usr/bin/env python

import unittest
from semanticfs.pathinfo import PathInfo


class PathInfoTests(unittest.TestCase):

    # path: (is_standard_object, is_tagged_object, is_tag, is_entrypoint)
    _testpaths = {"/a/b/c": (True, False, False, False),
                  "/a/b/_c": (False, False, False, True),
                  "/a/_b/c": (False, True, False, False),
                  "/a/_b/_c": (False, False, True, False),
                  "/_a/b/c": (True, False, False, False),
                  "/_a/b/_c": (False, False, False, True),
                  "/_a/_b/c": (False, True, False, False),
                  "/_a/_b/_c": (False, False, True, False),
                  "/": (True, False, False, False)
                  }

    def test_path_type_recognition(self):
        for k in self._testpaths.keys():
            with self.subTest(k=k):
                self.assertEqual(PathInfo(k).is_standard_object, self._testpaths[k][0], k)
                self.assertEqual(PathInfo(k).is_tagged_object, self._testpaths[k][1], k)
                self.assertEqual(PathInfo(k).is_tag, self._testpaths[k][2], k)
                self.assertEqual(PathInfo(k).is_entrypoint, self._testpaths[k][3], k)

    def test_relative_paths(self):
        self.assertRaises(ValueError, PathInfo, "a/b/c")
        self.assertRaises(ValueError, PathInfo, "")


def main():
    unittest.main()

if __name__ == '__main__':
    main()
