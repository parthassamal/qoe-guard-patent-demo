\
import unittest

from qoe_guard.diff import diff_json


class TestDiff(unittest.TestCase):
    def test_diff_basic(self):
        b = {"a": 1, "b": {"c": 2}, "d": [1, 2]}
        c = {"a": 2, "b": {"c": 2, "x": 9}, "d": [1, 2, 3]}
        changes = diff_json(b, c)
        paths = {ch.path for ch in changes}
        self.assertIn("$.a", paths)
        self.assertIn("$.b.x", paths)
        self.assertIn("$.d.__len__", paths)


if __name__ == "__main__":
    unittest.main()
