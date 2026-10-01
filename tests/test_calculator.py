import unittest
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

class TestCalculator(unittest.TestCase):
    def test_add(self):
        from calculator import add
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)

    def test_divide(self):
        from calculator import divide
        self.assertEqual(divide(10, 2), 5)
        self.assertEqual(divide(9, 3), 3)

    def test_divide_zero(self):
        from calculator import divide
        with self.assertRaises(ValueError):
            divide(5, 0)

if __name__ == "__main__":
    unittest.main()
