import unittest

import pandas as pd

from capital_dynamics.currency import column_unit, euro, export_frame


class CurrencyTests(unittest.TestCase):
    def test_euro_display_and_real_units(self):
        self.assertEqual(euro(1234.5), "€1,234.50")
        self.assertEqual(euro(-2), "€-2.00")
        self.assertEqual(euro(float("nan")), "Not recorded")
        self.assertEqual(column_unit("Real net wealth"), "EUR, year-0 prices")
        self.assertEqual(column_unit("Productive capacity"), "capital units")
        self.assertEqual(column_unit("Output"), "goods/year")
        self.assertEqual(column_unit("Age"), "")

    def test_exports_keep_numeric_euros_separate_from_physical_units_and_rates(self):
        frame = pd.DataFrame({"Money": [1.25], "Net wealth": [3.5], "Real net wealth": [3],
            "Output": [2], "Productive capacity": [4], "Age": [30], "rate": [.05]})
        exported = export_frame(frame)
        self.assertEqual(exported["Money (EUR)"][0], 1.25)
        self.assertEqual(exported["Real net wealth (EUR, year-0 prices)"][0], 3)
        self.assertEqual(exported["Output (goods/year)"][0], 2)
        self.assertEqual(exported["Productive capacity (capital units)"][0], 4)
        self.assertEqual(exported["Age"][0], 30)
        self.assertEqual(exported["rate"][0], .05)
        self.assertNotIn("Money (EUR)", frame)
        self.assertIn("Money (EUR)", exported.to_csv(index=False))
