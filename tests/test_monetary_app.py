import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class MonetaryAppTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40).run()
        app.segmented_control(key='economic_model').set_value('Monetary economy').run()
        self.assertFalse(app.exception)
        return app

    def test_sections_and_defaults(self):
        app = self.app()
        headings = [h.value for h in app.header]
        self.assertLess(headings.index('Government budget and taxes'), headings.index('UBI and pensions'))
        self.assertLess(headings.index('UBI and pensions'), headings.index('Healthcare, aging and mortality'))
        self.assertIn('Banking and credit', headings)
        self.assertIn('Money and prices', headings)
        self.assertEqual(app.number_input(key='m_initial_population').value, 100)
        self.assertEqual(app.number_input(key='m_initial_capacity').value, 200)
        self.assertEqual(app.number_input(key='m_healthcare_spending_fraction').value, 25)

    def test_budget_is_atomic_and_percentage_inputs_are_not_fractions(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        before = sim.config
        app.number_input(key='m_direct_redistribution_fraction').set_value(90.0)
        app.button(key='m_apply_allocation').click().run()
        self.assertEqual(sim.config, before)
        self.assertTrue(any('100%' in error.value for error in app.error))
        app.number_input(key='m_direct_redistribution_fraction').set_value(20.0)
        app.number_input(key='m_pension_budget_fraction').set_value(10.0)
        app.number_input(key='m_healthcare_spending_fraction').set_value(30.0)
        app.button(key='m_apply_allocation').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(sim.config.direct_redistribution_fraction, .2)
        self.assertEqual(sim.config.healthcare_spending_fraction, .3)
        self.assertEqual(sim.step_count, 0)
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertAlmostEqual(sim.budget_allocations['Healthcare'], sim.policy_budget * .3)

    def test_banking_and_printing_controls_preserve_state(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        app.toggle(key='m_lending_enabled').set_value(True)
        app.number_input(key='m_loan_spread').set_value(4.0)
        app.button(key='m_apply_banking').click().run()
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertEqual(sim.config.loan_spread, .04)
        app.toggle(key='m_monetary_financing').set_value(True)
        app.number_input(key='m_issuance_per_step').set_value(5.0)
        app.button(key='m_apply_money').click().run()
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(sim.history[-1]['Money issued'], 5)
        self.assertGreater(sim.history[-1]['Loans originated'], 0)
        self.assertAlmostEqual(sim.history[-1]['Money balance error'], 0)

    def test_comparison_reset_and_switching_models(self):
        app = self.app()
        legacy = app.session_state.simulation
        app.selectbox(key='m_comparison').select('Government bonds')
        app.button(key='m_load_comparison').click().run()
        sim = app.session_state.monetary_simulation
        self.assertTrue(sim.config.government_borrowing)
        app.number_input(key='m_years').set_value(2)
        app.button(key='m_advance').click().run()
        self.assertGreater(sim.government_debt, 0)
        app.segmented_control(key='economic_model').set_value('Legacy economy').run()
        self.assertIs(legacy, app.session_state.simulation)
        app.segmented_control(key='economic_model').set_value('Monetary economy').run()
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertFalse(app.session_state.monetary_running)
        app.button(key='m_reset').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.monetary_simulation.step_count, 0)
        self.assertTrue(app.session_state.monetary_simulation.config.government_borrowing)

    def test_live_pause_and_single_year(self):
        app = self.app()
        app.segmented_control(key='m_mode').set_value('Live').run()
        app.button(key='m_single_step').click().run()
        self.assertEqual(app.session_state.monetary_simulation.step_count, 1)
        app.button(key='m_toggle_live').click().run()
        self.assertTrue(app.session_state.monetary_running)
        self.assertTrue(app.button(key='m_single_step').disabled)
        year = app.session_state.monetary_simulation.step_count
        app.button(key='m_toggle_live').click().run()
        self.assertFalse(app.session_state.monetary_running)
        self.assertEqual(app.session_state.monetary_simulation.step_count, year)
        app.button(key='m_single_step').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.monetary_simulation.step_count, year + 1)

    def test_new_scenario_and_invalid_money_cap(self):
        app = self.app()
        app.number_input(key='m_money_cap').set_value(1.0)
        app.button(key='m_apply_money').click().run()
        self.assertEqual(app.session_state.monetary_simulation.config.money_cap, 0)
        self.assertTrue(app.error)
        app.number_input(key='m_initial_population').set_value(10)
        app.number_input(key='m_initial_capacity').set_value(50.0)
        app.button(key='m_new_scenario').click().run()
        self.assertFalse(app.exception)
        sim = app.session_state.monetary_simulation
        self.assertEqual(len(sim.population), 10)
        self.assertEqual(sim.capacity, 50)
        app.selectbox(key='m_comparison').select('No credit or printing')
        app.button(key='m_load_comparison').click().run()
        self.assertEqual(app.number_input(key='m_initial_population').value, 100)
        self.assertEqual(app.number_input(key='m_initial_capacity').value, 200)

    def test_fragment_only_refresh(self):
        source = (Path(__file__).resolve().parents[1] / 'app.py').read_text()
        # Add a fragment-refresh trigger before st.stop in the monetary branch.
        source = source.replace('    st.stop()', '\n    def refresh_monetary():\n        st.rerun("monetary_dashboard")\n'
            '    st.button("Refresh monetary dashboard", key="m_test_refresh", on_click=refresh_monetary)\n    st.stop()')
        app = AppTest.from_string(source, default_timeout=40).run()
        app.segmented_control(key='economic_model').set_value('Monetary economy').run()
        charts = len(app.get('vega_lite_chart'))
        app.button(key='m_test_refresh').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('vega_lite_chart')), charts)

    def test_reset_rejects_cap_below_initial_supply_without_crashing(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        sim.update_policy(lending_enabled=True, loan_term=1, policy_rate=.05, loan_spread=0)
        person = sim.population[0]
        person.age = 30
        sim.originate_loan(person, 1)
        sim.step_count = 1
        sim.service_loans()
        sim.update_policy(money_cap_type='Broad money', money_cap=sim.broad_money)
        app.button(key='m_reset').click().run()
        self.assertFalse(app.exception)
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertTrue(any('starting supply' in e.value for e in app.error))
