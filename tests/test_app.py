import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()

    def test_private_investment_risk_controls_apply_to_the_model(self):
        app = self.app()
        app.number_input(key='config_investment_risk').set_value(1.0)
        app.number_input(key='config_failed_investment_loss').set_value(0.5)
        app.number_input(key='config_gain_prob').set_value(1.0)
        app.number_input(key='config_gain_fraction').set_value(1.0)
        app.button(key='apply_private_investments').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.simulation.config.investment_risk, 1.0)
        self.assertEqual(app.session_state.simulation.config.failed_investment_loss, 0.5)
        app.number_input(key='batch_steps').set_value(1)
        app.button(key='advance').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.simulation.history[-1]['Failed private investments'], app.session_state.simulation.config.pop_size)
        self.assertGreater(app.session_state.simulation.history[-1]['Private investment losses'], 0)

    def test_healthcare_controls_and_age_curves(self):
        app = self.app()
        app.number_input(key='config_healthcare_spending_fraction').set_value(0.5)
        app.number_input(key='config_healthcare_response_rate').set_value(1.0)
        app.button(key='apply_healthcare').click().run()
        app.number_input(key='config_tau_base').set_value(0.01)
        app.button(key='apply_taxes').click().run()
        app.number_input(key='batch_steps').set_value(1)
        app.button(key='advance').click().run()
        self.assertFalse(app.exception)
        sim = app.session_state.simulation
        self.assertGreater(sim.healthcare_spending, 0)
        self.assertLess(sim.mortality_rate, sim.config.death_base_prob)
        self.assertGreater(sim.death_probability(80, 1), sim.death_probability(20, 1))

    def test_pension_and_private_care_controls_affect_personal_wealth(self):
        app = self.app()
        app.number_input(key='config_retirement_age').set_value(0)
        app.number_input(key='config_pension_budget_fraction').set_value(0.5)
        app.button(key='apply_pensions').click().run()
        app.number_input(key='config_tau_base').set_value(0.01)
        app.button(key='apply_taxes').click().run()
        app.selectbox(key='config_healthcare_choice_mode').select('Private if affordable')
        app.button(key='apply_private_healthcare').click().run()
        app.number_input(key='batch_steps').set_value(1)
        app.button(key='advance').click().run()
        self.assertFalse(app.exception)
        sim = app.session_state.simulation
        self.assertGreater(sim.pension_spending, 0)
        self.assertGreater(sim.private_healthcare_revenue, 0)
        self.assertTrue(any(p.pension_received > 0 and p.healthcare_premium > 0 for p in sim.population))
        self.assertAlmostEqual(sim.history[-1]['Government balance error'], 0)

    def test_policy_changes_keep_the_running_economy_and_history(self):
        app = self.app()
        app.segmented_control(key='mode').set_value('Live').run()
        app.button(key='start').click().run()
        before = app.session_state.simulation
        history = list(before.history)
        old_step = before.step_count
        app.number_input(key='config_tau_base').set_value(0.01)
        app.number_input(key='config_direct_redistribution_fraction').set_value(0.25)
        app.button(key='apply_taxes').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state.running)
        self.assertIs(before, app.session_state.simulation)
        self.assertEqual(before.config.tau_base, 0.01)
        self.assertEqual(before.step_count, old_step + 1)
        self.assertEqual(list(before.history)[:len(history)], history)
        self.assertGreater(before.history[-1]['Tax revenue'], 0)
        self.assertEqual(before.policy_changes[-1]['Effective step'], old_step + 1)
        app.button(key='pause').click().run()
        app.number_input(key='config_healthcare_spending_fraction').set_value(0.8)
        app.button(key='apply_healthcare').click().run()
        self.assertEqual(before.step_count, old_step + 1)
        self.assertEqual(before.config.healthcare_spending_fraction, 0.8)
        self.assertFalse(app.session_state.running)
        app.button(key='single_step').click().run()
        self.assertGreater(before.healthcare_spending, 0)
        self.assertFalse(app.exception)

    def test_invalid_tax_policy_keeps_the_active_config(self):
        app = self.app()
        before = app.session_state.simulation.config
        app.number_input(key='config_tau_base').set_value(0.8)
        app.number_input(key='config_tau_max').set_value(0.2)
        app.button(key='apply_taxes').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.simulation.config, before)
        self.assertTrue(any('maximum tax rate' in e.value for e in app.error))

    def test_old_session_is_repaired_before_a_policy_callback(self):
        app = self.app()
        app.number_input(key='batch_steps').set_value(3)
        app.button(key='advance').click().run()
        previous = app.session_state.simulation
        history = list(previous.history)
        del previous.policy_changes
        del previous.initial_config
        app.number_input(key='config_tau_base').set_value(0.01)
        app.button(key='apply_taxes').click().run()
        self.assertFalse(app.exception)
        restored = app.session_state.simulation
        self.assertEqual(restored.step_count, 3)
        self.assertEqual(list(restored.history), history)
        self.assertEqual(restored.config.tau_base, 0.01)
        self.assertEqual(restored.policy_changes[-1]['Effective step'], 4)
        app.number_input(key='batch_steps').set_value(1)
        app.button(key='advance').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(restored.step_count, 4)

    def test_metrics_and_tax_curve_are_in_the_relevant_sections(self):
        app = self.app()
        self.assertFalse(app.exception)
        nodes = list(app)
        def heading(title):
            return next(i for i,n in enumerate(nodes) if n.type == 'header' and n.value == title)
        gini = next(i for i,n in enumerate(nodes) if n.type == 'metric' and n.label == 'Gini coefficient')
        budget = next(i for i,n in enumerate(nodes) if n.type == 'metric' and n.label == 'Government budget')
        self.assertLess(heading('Current wealth distribution'), gini)
        self.assertLess(gini, heading('Economy over time'))
        self.assertLess(heading('Government spending and UBI'), budget)
        self.assertLess(budget, heading('Healthcare, aging and mortality'))
        self.assertTrue(any(n.value == 'Current wealth tax curve' for n in app.subheader))
        self.assertTrue(any(n.label == 'UBI per person' for n in app.metric))

    def test_load_defaults_resets_active_and_displayed_parameters(self):
        app = self.app()
        app.number_input(key='config_pop_size').set_value(10)
        app.button(key='new_scenario').click().run()
        app.number_input(key='config_tau_base').set_value(0.01)
        app.button(key='apply_taxes').click().run()
        app.button(key='load_defaults').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.simulation.step_count, 0)
        self.assertEqual(app.session_state.simulation.config.pop_size, 300)
        self.assertEqual(app.number_input(key='config_pop_size').value, 300)
        self.assertEqual(app.number_input(key='config_tau_base').value, 0.005)

    def test_batch_live_pause_resume_and_reset(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('vega_lite_chart')), 15)
        app.number_input(key='batch_steps').set_value(5)
        app.button(key='advance').click().run()
        self.assertEqual(app.session_state.simulation.step_count, 5)
        app.segmented_control(key='mode').set_value('Live').run()
        app.button(key='single_step').click().run()
        self.assertEqual(app.session_state.simulation.step_count, 6)
        app.button(key='start').click().run()
        self.assertTrue(app.session_state.running)
        before = app.session_state.simulation.step_count
        app.button(key='pause').click().run()
        self.assertFalse(app.session_state.running)
        self.assertEqual(app.session_state.simulation.step_count, before)
        app.slider(key='groups').set_value(5).run()
        self.assertEqual(app.session_state.simulation.step_count, before)
        app.button(key='start').click().run()
        self.assertGreater(app.session_state.simulation.step_count, before)
        app.button(key='reset').click().run()
        self.assertEqual(app.session_state.simulation.step_count, 0)
        self.assertFalse(app.session_state.running)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
