import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class MonetaryAppTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40).run()
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
        self.assertEqual(app.number_input(key='m_tau_base').value, 0)
        self.assertEqual(app.number_input(key='m_tau_max').value, 60)
        # Defaults must be in the widget proto, not only session-state overrides:
        # otherwise closed settings can remount at their minima after live ticks.
        self.assertEqual(app.number_input(key='m_tau_max').proto.default, 60)
        self.assertEqual(app.number_input(key='m_ubi_budget_fraction').proto.default, 25)
        self.assertEqual(app.number_input(key='m_initial_producer').proto.default, 100)

    def test_technology_controls_apply_and_breakthroughs_are_reported(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        self.assertEqual(app.number_input(key='m_productivity_growth').value, 1)
        app.number_input(key='m_technology_breakthrough_probability').set_value(100.0)
        app.number_input(key='m_technology_gain_min').set_value(10.0)
        app.number_input(key='m_technology_gain_max').set_value(10.0)
        app.button(key='m_apply_production').click().run()
        self.assertEqual(sim.config.technology_breakthrough_probability, 1)
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(sim.technology_breakthroughs, 1)
        self.assertAlmostEqual(sim.technology_index, 1.111)
        self.assertIn('Technology breakthrough history', [heading.value for heading in app.subheader])
        self.assert_explanatory_help(app)

    def test_firm_scenario_controls_jobs_and_business_reporting(self):
        app = self.app()
        app.number_input(key='m_initial_firms').set_value(3)
        app.number_input(key='m_firm_dispersion').set_value(0.0)
        app.button(key='m_new_scenario').click().run()
        sim = app.session_state.monetary_simulation
        self.assertEqual(len(sim.market.active), 3)
        self.assertEqual(sim.step_count, 0)
        self.assertIsNone(sim.history[0]['Unemployment rate'])
        app.number_input(key='m_inventory_spoilage').set_value(5.0)
        app.number_input(key='m_research_spending_fraction').set_value(20.0)
        app.toggle(key='m_business_lending').set_value(True)
        app.button(key='m_apply_firms').click().run()
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertEqual(sim.config.inventory_spoilage, .05)
        self.assertEqual(sim.config.research_spending_fraction, .2)
        self.assertTrue(sim.config.business_lending)
        app.number_input(key='m_years').set_value(2)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        labels = [item.label for item in app.metric]
        self.assertIn('Unemployment rate', labels)
        self.assertIn('Active firms', labels)
        self.assertIn('Research spending', labels)
        self.assertIn('Download firm accounts CSV', [item.label for item in app.get('download_button')])
        self.assertIn('Firm accounts and competition', [item.value for item in app.subheader])
        self.assertAlmostEqual(sim.flows['Inventory balance error'], 0)

    def test_education_controls_budget_and_delayed_teaching(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        self.assertIn('Education, skills and retraining', [item.value for item in app.header])
        self.assertEqual(app.number_input(key='m_education_budget_fraction').value, 10)
        app.number_input(key='m_university_duration').set_value(4)
        app.number_input(key='m_retraining_participation').set_value(50.0)
        app.button(key='m_apply_education').click().run()
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertEqual(sim.config.university_duration, 4)
        self.assertEqual(sim.config.retraining_participation, .5)
        app.number_input(key='m_years').set_value(2)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(sim.history[1]['Teachers'], 0)
        self.assertGreater(sim.history[-1]['Teachers'], 0)
        self.assertGreater(sim.history[-1]['Education spent'], 0)
        labels = [item.label for item in app.metric]
        self.assertIn('Education quality', labels)
        self.assertIn('Mean worker skill', labels)
        self.assert_explanatory_help(app)

    def test_energy_controls_and_queued_supply_shock(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        self.assertIn('Energy and supply shocks', [item.value for item in app.header])
        app.number_input(key='m_energy_shock_probability').set_value(0.0)
        app.number_input(key='m_energy_shock_severity').set_value(100.0)
        app.number_input(key='m_energy_shock_duration').set_value(2)
        app.button(key='m_apply_energy').click().run()
        self.assertEqual(sim.config.energy_shock_severity, 1)
        self.assertEqual(sim.step_count, 0)
        app.button(key='m_queue_energy_shock').click().run()
        self.assertTrue(sim.energy.shock_pending)
        self.assertFalse(app.session_state.monetary_running)
        app.button(key='m_cancel_energy_shock').click().run()
        self.assertFalse(sim.energy.shock_pending)
        app.button(key='m_queue_energy_shock').click().run()
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(sim.energy.shock_pending)
        self.assertEqual(sim.history[-1]['Energy available'], 0)
        self.assertEqual(sim.output, 0)
        self.assertEqual(sim.energy.shock_remaining, 1)
        self.assertIn('Energy shock history', [item.value for item in app.subheader])
        self.assert_explanatory_help(app)

    def assert_explanatory_help(self, app):
        for kind in ('number_input', 'selectbox', 'slider', 'select_slider', 'toggle',
                     'segmented_control', 'button', 'download_button', 'metric', 'checkbox'):
            for element in app.get(kind):
                with self.subTest(kind=kind, label=element.label):
                    help_text = element.proto.help.strip()
                    self.assertTrue(help_text)
                    self.assertNotEqual(help_text, element.label)
        for element in app.get('popover'):
            self.assertTrue(element.proto.popover.help.strip())

    def test_tooltips_cover_batch_and_live_controls_metrics_and_downloads(self):
        app = self.app()
        self.assert_explanatory_help(app)
        app.segmented_control(key='m_mode').set_value('Live').run()
        self.assertFalse(app.exception)
        self.assert_explanatory_help(app)
        app.button(key='m_toggle_live').click().run()
        self.assertFalse(app.exception)
        self.assert_explanatory_help(app)
        app.button(key='m_toggle_live').click().run()
        self.assertFalse(app.exception)
        self.assert_explanatory_help(app)

    def test_every_monetary_policy_has_specific_help(self):
        from capital_dynamics.help_text import POLICY_HELP
        from capital_dynamics.monetary_ui import SPECS

        app = self.app()
        for specs in SPECS.values():
            for name, label, *_ in specs:
                with self.subTest(policy=name):
                    self.assertIn(name, POLICY_HELP)
                    self.assertNotEqual(POLICY_HELP[name], label)
                    element = next(
                        widget for kind in ('number_input', 'selectbox', 'toggle')
                        for widget in app.get(kind) if widget.key == f'm_{name}'
                    )
                    self.assertEqual(element.proto.help, POLICY_HELP[name])
        self.assertIn('not a full save-state', app.get('download_button')[-1].proto.help)
        self.assertIn('Replace the current economy', app.button(key='m_new_scenario').proto.help)

    def test_euro_amounts_and_physical_units_are_explicit(self):
        from capital_dynamics.monetary_ui import table_columns
        import pandas as pd

        app = self.app()
        money_metrics = {
            'Nominal net wealth', 'Real net wealth', 'Government money', 'Government debt',
            'Debt service shortfall', 'Tax revenue last year', 'Government cash outflows last year',
            'UBI paid', 'Pensions paid', 'Unfunded pension entitlement', 'Public healthcare paid',
            'Private premiums paid', 'Healthcare sector money', 'Bank equity',
            'Outstanding household loans', 'Loan defaults this year', 'Base money', 'Broad money',
        }
        for metric in app.metric:
            if metric.label in money_metrics:
                self.assertTrue(metric.value.startswith('€'), metric.label)
        for key in ('m_initial_money', 'm_initial_producer', 'm_initial_bank',
                    'm_borrowing_target', 'm_debt_ceiling', 'm_issuance_per_step', 'm_money_cap'):
            self.assertIn('€', app.number_input(key=key).label)
        columns = table_columns(pd.DataFrame(columns=['Money', 'Real net wealth', 'Productive capacity', 'Age']))
        self.assertEqual(columns['Money']['label'], 'Money (EUR)')
        self.assertEqual(columns['Real net wealth']['label'], 'Real net wealth (EUR, year-0 prices)')
        self.assertEqual(columns['Productive capacity']['label'], 'Productive capacity (capital units)')
        self.assertTrue(any('euro' in caption.value.lower() for caption in app.caption))

    def test_living_standards_and_credit_risk_controls(self):
        from capital_dynamics.currency import euro

        app = self.app()
        self.assertIn('Living standards and income', [h.value for h in app.header])
        metric = lambda label: next(item for item in app.metric if item.label == label)
        self.assertEqual(metric('Median disposable income').value, 'Not recorded')
        self.assertEqual(metric('Pension replacement ratio').value, 'Not recorded')
        self.assertEqual(app.number_input(key='m_debt_service_limit').value, 35)
        self.assertEqual(app.number_input(key='m_income_stress_fraction').value, 20)
        app.number_input(key='m_debt_service_limit').set_value(25.0)
        app.number_input(key='m_collateral_recovery_haircut').set_value(40.0)
        app.button(key='m_apply_banking').click().run()
        sim = app.session_state.monetary_simulation
        self.assertEqual(sim.config.debt_service_limit, .25)
        self.assertEqual(sim.config.collateral_recovery_haircut, .4)
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(metric('Median disposable income').value, euro(sim.history[-1]['Median disposable income']))
        self.assertEqual(metric('Prudential bank equity').value, euro(sim.prudential_equity))
        self.assertTrue(any('not the official EU poverty rate' in caption.value for caption in app.caption))
        self.assertIn('Official data references and calibration status', [item.label for item in app.expander])

    def test_sovereign_default_requires_confirmation_and_executes_next_year(self):
        app = self.app()
        self.assertNotIn('m_debt_service_fraction', [widget.key for widget in app.number_input])
        self.assertTrue(app.button(key='m_queue_default').disabled)
        app.selectbox(key='m_comparison').select('Government bonds')
        app.button(key='m_load_comparison').click().run()
        app.number_input(key='m_years').set_value(2)
        app.button(key='m_advance').click().run()
        sim = app.session_state.monetary_simulation
        self.assertGreater(sim.government_debt, 0)
        self.assertTrue(app.button(key='m_queue_default').disabled)
        app.checkbox(key='m_confirm_sovereign_default').check().run()
        self.assertFalse(app.button(key='m_queue_default').disabled)
        app.button(key='m_queue_default').click().run()
        self.assertTrue(sim.sovereign_default_pending)
        self.assertEqual(sim.sovereign_default_count, 0)
        self.assertFalse(app.session_state.monetary_running)
        app.button(key='m_cancel_default').click().run()
        self.assertFalse(sim.sovereign_default_pending)
        app.button(key='m_queue_default').click().run()
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(sim.sovereign_default_pending)
        self.assertFalse(sim.bonds)
        self.assertEqual(sim.sovereign_default_count, 1)
        self.assertFalse(sim.sovereign_market_access)
        self.assertGreater(sim.history[-1]['Sovereign debt written off'], 0)
        self.assertGreater(sim.history[-1]['Sovereign spread'], sim.config.sovereign_base_spread)
        self.assertIn('Sovereign default history', [heading.value for heading in app.subheader])

    def test_budget_is_atomic_and_percentage_inputs_are_not_fractions(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        before = sim.config
        app.number_input(key='m_ubi_budget_fraction').set_value(90.0)
        app.button(key='m_apply_allocation').click().run()
        self.assertEqual(sim.config, before)
        self.assertTrue(any('100%' in error.value for error in app.error))
        app.number_input(key='m_ubi_budget_fraction').set_value(20.0)
        app.number_input(key='m_pension_budget_fraction').set_value(10.0)
        app.number_input(key='m_healthcare_spending_fraction').set_value(30.0)
        app.button(key='m_apply_allocation').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(sim.config.ubi_budget_fraction, .2)
        self.assertEqual(sim.config.healthcare_spending_fraction, .3)
        self.assertEqual(sim.step_count, 0)
        app.number_input(key='m_years').set_value(1)
        app.button(key='m_advance').click().run()
        self.assertAlmostEqual(sim.budget_allocations['Healthcare'], sim.policy_budget * .3)

    def test_banking_and_printing_controls_preserve_state(self):
        app = self.app()
        sim = app.session_state.monetary_simulation
        # Make wages available for repayment; default wealth taxes can absorb
        # current wages and legitimately prevent new borrowing.
        app.number_input(key='m_tau_max').set_value(0.0)
        app.button(key='m_apply_taxes').click().run()
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

    def test_comparison_reset_and_retained_economy(self):
        app = self.app()
        app.selectbox(key='m_comparison').select('Government bonds')
        app.button(key='m_load_comparison').click().run()
        sim = app.session_state.monetary_simulation
        self.assertTrue(sim.config.government_borrowing)
        app.number_input(key='m_years').set_value(2)
        app.button(key='m_advance').click().run()
        self.assertGreater(sim.government_debt, 0)
        app.run()
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertFalse(app.session_state.monetary_running)
        app.button(key='m_reset').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.monetary_simulation.step_count, 0)
        self.assertTrue(app.session_state.monetary_simulation.config.government_borrowing)

    def test_live_pause_and_single_year(self):
        app = self.app()
        app.segmented_control(key='m_mode').set_value('Live').run()
        self.assertEqual(app.button(key='m_toggle_live').label, 'Start')
        app.button(key='m_single_step').click().run()
        self.assertEqual(app.session_state.monetary_simulation.step_count, 1)
        app.button(key='m_toggle_live').click().run()
        self.assertTrue(app.session_state.monetary_running)
        self.assertTrue(app.button(key='m_single_step').disabled)
        year = app.session_state.monetary_simulation.step_count
        app.button(key='m_toggle_live').click().run()
        self.assertFalse(app.session_state.monetary_running)
        self.assertEqual(app.button(key='m_toggle_live').label, 'Resume')
        self.assertEqual(app.session_state.monetary_simulation.step_count, year)
        app.button(key='m_single_step').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.monetary_simulation.step_count, year + 1)

    def test_restored_charts_and_display_controls(self):
        app = self.app()
        titles = [s.value for s in app.subheader]
        for title in ('Wealth by population percentile', 'Net wealth inequality over time', 'Current net wealth tax curve',
                      'Applied net wealth tax rates', 'Government money and debt', 'Mortality over time', 'Healthcare choices over time'):
            self.assertIn(title, titles)
        charts = len(app.get('vega_lite_chart'))
        app.slider(key='m_groups').set_value(5).run()
        app.select_slider(key='m_age_bin').set_value(5).run()
        app.segmented_control(key='m_age_unit').set_value('People').run()
        app.toggle(key='m_log_wealth').set_value(True).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('vega_lite_chart')), charts)
        self.assertEqual(app.session_state.monetary_simulation.step_count, 0)
        app.toggle(key='m_show_individuals').set_value(False).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('vega_lite_chart')), charts - 1)

    def test_settings_are_flat_borderless_forms_with_compact_budget_fields(self):
        app = self.app()
        for form in app.get('form'):
            self.assertFalse(form.proto.form.border)
        self.assertTrue(any(n.key == 'm_settings_allocation' for n in app.get('popover')))
        self.assertEqual(app.number_input(key='m_ubi_budget_fraction').label, 'UBI (%)')
        app.number_input(key='m_tau_max').set_value(50.0)
        app.button(key='m_apply_taxes').click().run()
        app.segmented_control(key='m_mode').set_value('Live').run()
        app.button(key='m_single_step').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='m_tau_max').proto.default, 50)
        self.assertEqual(app.number_input(key='m_ubi_budget_fraction').proto.default, 25)

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
        source += '\n\ndef refresh_monetary():\n    st.rerun("monetary_dashboard")\n'
        source += '\nst.button("Refresh monetary dashboard", key="m_test_refresh", on_click=refresh_monetary)\n'
        app = AppTest.from_string(source, default_timeout=40).run()
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
        person.last_repayment_income = 100
        person.income_observed = True
        sim.originate_loan(person, 1)
        sim.step_count = 1
        sim.service_loans()
        sim.update_policy(money_cap_type='Broad money', money_cap=sim.broad_money)
        app.button(key='m_reset').click().run()
        self.assertFalse(app.exception)
        self.assertIs(sim, app.session_state.monetary_simulation)
        self.assertTrue(any('starting supply' in e.value for e in app.error))
