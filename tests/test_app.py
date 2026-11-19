"""Entrypoint and reporting regressions for the single monetary dashboard."""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40).run()
        self.assertFalse(app.exception)
        return app

    def test_monetary_is_the_only_dashboard(self):
        app = self.app()
        self.assertNotIn('economic_model', [w.key for w in app.segmented_control])
        self.assertNotIn('simulation', app.session_state)
        self.assertEqual(app.session_state.monetary_simulation.step_count, 0)
        self.assertEqual(len(app.header), 9)

    def test_reporting_and_downloads_cover_legacy_categories(self):
        app = self.app()
        titles = [s.value for s in app.subheader]
        for title in ('Net wealth of each individual', 'Wealth by population percentile',
                      'Net wealth inequality over time', 'Real household net wealth and productive capacity',
                      'Population and deaths', 'Government money and debt', 'Current net wealth tax curve',
                      'Applied net wealth tax rates', 'Government expenditure by policy',
                      'Mortality over time', 'Healthcare funding', 'Healthcare choices over time',
                      'Private investment outcomes'):
            self.assertIn(title, titles)
        labels = [w.label for w in app.get('download_button')]
        for label in ('Download monetary history CSV', 'Download monetary population CSV',
                      'Download finance ledger CSV', 'Download monetary scenario settings',
                      'Download transaction ledger CSV', 'Download sector balance sheets CSV'):
            self.assertIn(label, labels)

    def test_policy_edits_preserve_live_economy(self):
        app = self.app()
        app.segmented_control(key='m_mode').set_value('Live').run()
        app.button(key='m_toggle_live').click().run()
        sim = app.session_state.monetary_simulation
        history = list(sim.history)
        year = sim.step_count
        app.number_input(key='m_tau_base').set_value(1.0)
        app.button(key='m_apply_taxes').click().run()
        self.assertFalse(app.exception)
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertTrue(app.session_state.monetary_running)
        self.assertEqual(sim.config.tau_base, .01)
        self.assertEqual(sim.step_count, year + 1)
        self.assertEqual(list(sim.history)[:len(history)], history)

    def test_invalid_tax_policy_is_atomic(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        config = sim.config
        app.number_input(key='m_tau_base').set_value(80.0)
        app.number_input(key='m_tau_max').set_value(20.0)
        app.button(key='m_apply_taxes').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(sim.config, config)
        self.assertTrue(app.error)

    def test_new_scenario_and_display_changes(self):
        app = self.app()
        self.assertTrue(all(not f.proto.form.enter_to_submit for f in app.get('form')))
        app.number_input(key='m_seed').set_value(425)
        app.number_input(key='m_initial_population').set_value(10)
        app.button(key='m_new_scenario').click().run()
        sim = app.session_state.monetary_simulation
        self.assertEqual(sim.seed, 425)
        self.assertEqual(len(sim.population), 10)
        app.number_input(key='m_years').set_value(2)
        app.button(key='m_advance').click().run()
        app.slider(key='m_groups').set_value(5).run()
        self.assertFalse(app.exception)
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertEqual(sim.step_count, 2)

    def test_old_monetary_history_is_not_backfilled(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        missing = ('Opening government money', 'Total government spending', 'Government balance error',
                   'Failed private investments', 'Private capital added', 'Private capital shortfall')
        for key in missing:
            sim.history[0].pop(key)
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(all(key not in sim.history[0] for key in missing))
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(all(key in sim.history[-1] for key in missing))


if __name__ == '__main__':
    unittest.main()
