import unittest

from capital_dynamics.calibration import REFERENCE_BENCHMARKS, RELATIVE_LOW_INCOME_FRACTION, RETRIEVED_ON
from capital_dynamics.currency import column_unit
from capital_dynamics.monetary import MonetaryConfig


class CalibrationTests(unittest.TestCase):
    def test_references_are_dated_explicit_and_do_not_replace_defaults(self):
        self.assertEqual(RETRIEVED_ON, "2026-11-19")
        self.assertEqual(RELATIVE_LOW_INCOME_FRACTION, .6)
        self.assertEqual(MonetaryConfig().initial_money_per_person, 1)
        for reference in REFERENCE_BENCHMARKS:
            for field in ("Indicator", "Observation", "Area", "Period", "Source", "Use"):
                self.assertTrue(reference[field])
            self.assertTrue(reference["Source"].startswith("https://"))
        self.assertIn("statinfo=MED_EI", REFERENCE_BENCHMARKS[0]["Source"])
        self.assertIn("not personal income", REFERENCE_BENCHMARKS[0]["Use"])

    def test_credit_and_living_standard_export_units(self):
        for name in ("Loan recoveries", "Loan principal losses", "Bank realized profit",
                     "Prudential bank equity", "Unpaid loan interest", "Median disposable income",
                     "Consumption per person", "Disposable income", "Verified repayment income"):
            self.assertEqual(column_unit(name), "EUR", name)
        self.assertEqual(column_unit("Median real disposable income"), "EUR, year-0 prices")
        self.assertEqual(column_unit("Real consumption per person"), "goods/person/year")
        for name in ("Borrower risk score", "Relative low-income share", "Pension replacement ratio"):
            self.assertEqual(column_unit(name), "")
