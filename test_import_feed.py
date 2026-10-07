import unittest
from import_feed import parse_composition

class CompositionTests(unittest.TestCase):
    def test_natural(self):
        r = parse_composition("55% linen, 45% cotton")
        self.assertTrue(r["strict_natural"])
        self.assertTrue(r["non_synthetic"])

    def test_synthetic(self):
        r = parse_composition("98% cotton, 2% elastane")
        self.assertFalse(r["strict_natural"])
        self.assertFalse(r["non_synthetic"])

    def test_regenerated(self):
        r = parse_composition("50% modal, 50% linen")
        self.assertFalse(r["strict_natural"])
        self.assertTrue(r["non_synthetic"])

    def test_lining_catches_synthetic(self):
        r = parse_composition("Outer: 100% cotton. Lining: 100% polyester")
        self.assertFalse(r["strict_natural"])
        self.assertFalse(r["non_synthetic"])

    def test_unclear_needs_review(self):
        r = parse_composition("Cotton blend")
        self.assertTrue(r["needs_review"])

if __name__ == "__main__":
    unittest.main()
