import unittest
from slug import slug


class SlugTests(unittest.TestCase):
    def test_simple_title(self):
        self.assertEqual(slug("Hello World"), "hello-world")

    def test_repeated_spaces(self):
        self.assertEqual(slug("Hello   World"), "hello-world")

    def test_surrounding_whitespace(self):
        self.assertEqual(slug("  Good Morning  "), "good-morning")

