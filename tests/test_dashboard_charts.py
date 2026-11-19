import unittest

import pandas as pd

from budget import COLORS
from dashboard_charts import distribution_data, series_scale


class DashboardChartTests(unittest.TestCase):
    def test_equal_wealth_percentiles_have_stable_groups(self):
        people = pd.DataFrame({'Person': range(10), 'Age': [30] * 10, 'Net wealth': [3.0] * 10})
        ordered, shares, labels = distribution_data(people, 5, 'Net wealth')
        self.assertEqual(ordered['Rank'].tolist(), list(range(1, 11)))
        self.assertEqual(ordered['Group index'].tolist(), [0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
        self.assertEqual(shares['Wealth share'].tolist(), [.2] * 5)
        self.assertEqual(shares['Group index'].tolist(), list(range(5)))
        self.assertEqual(shares['Percentile group'].tolist(), labels)

    def test_negative_wealth_is_not_clipped_out_of_group_data(self):
        people = pd.DataFrame({'Person': [0, 1], 'Age': [30, 40], 'Net wealth': [-2.0, 5.0]})
        _, shares, _ = distribution_data(people, 2, 'Net wealth')
        self.assertEqual(shares['Net wealth'].tolist(), [-2, 5])
        self.assertAlmostEqual(shares['Wealth share'].sum(), 1)

    def test_empty_population_has_zero_shares(self):
        people = pd.DataFrame(columns=['Person', 'Age', 'Wealth'])
        _, shares, _ = distribution_data(people, 10)
        self.assertEqual(shares.Wealth.sum(), 0)
        self.assertEqual(shares['Wealth share'].sum(), 0)

    def test_policy_colors_are_consistent_across_charts(self):
        names = ['UBI spent', 'Pensions spent', 'Healthcare spent', 'Public investment spent', 'Debt service spent']
        self.assertEqual(series_scale(names).to_dict()['range'], COLORS[:5])
