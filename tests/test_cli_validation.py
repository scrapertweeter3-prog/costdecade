"""CLI input validation: numbers from the command line, not just from CSV."""
import pathlib
import subprocess
import sys
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "costdecade.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


class CliRangeTests(unittest.TestCase):
    def assert_rejected(self, *args):
        res = run(*args)
        self.assertEqual(res.returncode, 2, res.stderr)
        self.assertIn("error:", res.stderr)

    def test_zero_life_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "0")
        self.assertIn("--life must be positive", run(
            "--price", "100", "--life", "0").stderr)

    def test_negative_life_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "-3")

    def test_negative_price_is_rejected(self):
        self.assert_rejected("--price", "-100", "--life", "5")

    def test_zero_rival_life_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "5",
                             "--rival-price", "50", "--rival-life", "0")

    def test_negative_rival_price_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "5",
                             "--rival-price", "-50", "--rival-life", "2")

    def test_zero_horizon_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "5", "--horizon", "0")

    def test_negative_inflation_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "5", "--inflation", "-2")

    def test_resale_out_of_range_is_rejected(self):
        self.assert_rejected("--price", "100", "--life", "5", "--resale", "150")
        self.assert_rejected("--price", "100", "--life", "5", "--resale", "-1")

    def test_valid_numbers_still_work(self):
        res = run("--price", "340", "--life", "10",
                  "--rival-price", "120", "--rival-life", "2")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("winner: item", res.stdout)

    def test_zero_resale_is_allowed(self):
        res = run("--price", "100", "--life", "5", "--resale", "0")
        self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()
