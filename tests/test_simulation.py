import unittest
from unittest.mock import patch
from dataclasses import replace

from capital_dynamics.simulation import Individual, Simulation, SimulationConfig, restore_simulation, wealth_tax_rates, tax_rates_at_relative_wealth


class SimulationTests(unittest.TestCase):
    def test_resuming_matches_one_uninterrupted_run(self):
        config = SimulationConfig(pop_size=50)
        whole = Simulation(config, seed=7)
        whole.advance(50)
        resumed = Simulation(config, seed=7)
        resumed.advance(20)
        # Another session must not change this simulation's random sequence.
        Simulation(config, seed=123).advance(15)
        resumed.advance(30)
        self.assertEqual(whole.result(), resumed.result())
        self.assertEqual(whole.population[0].age, resumed.population[0].age)

    def test_age_and_step_advance_once(self):
        sim = Simulation(SimulationConfig(pop_size=1, birth_prob_max=0, death_base_prob=0, aging_risk_rate=0))
        age = sim.population[0].age
        sim.step()
        self.assertEqual(sim.population[0].age, age + 1)
        self.assertEqual(sim.step_count, 1)

    def test_history_window_does_not_stop_simulation(self):
        sim = Simulation(SimulationConfig(pop_size=1, birth_prob_max=0, death_base_prob=0, aging_risk_rate=0), history_limit=3)
        sim.advance(10)
        self.assertEqual(sim.step_count, 10)
        self.assertEqual([row['Step'] for row in sim.history], [8, 9, 10])

    def test_private_opportunity_success_and_failure(self):
        config = SimulationConfig(pop_size=1, init_wealth=10, logistic_capacity=1000, base_growth=0,
                                  gain_prob=1, gain_fraction=1, gain_growth=0.2,
                                  loss_prob=0, tau_base=0, tau_max=0,
                                  birth_prob_max=0, death_base_prob=0,
                                  investment_probability=0, aging_risk_rate=0)
        success = Simulation(replace(config, investment_risk=0))
        success.step()
        self.assertAlmostEqual(success.population[0].wealth, 11.98)
        self.assertAlmostEqual(success.history[-1]['Private investment gains'], 1.98)
        self.assertEqual(success.history[-1]['Failed private investments'], 0)
        failure = Simulation(replace(config, investment_risk=1, failed_investment_loss=0.25))
        failure.step()
        self.assertEqual(failure.population[0].wealth, 7.5)
        self.assertEqual(failure.history[-1]['Private investment losses'], 2.5)
        self.assertEqual(failure.history[-1]['Failed private investments'], 1)
        self.assertEqual(failure.history[-1]['Private investment gains'], 0)

    def test_private_failure_at_capacity_and_with_zero_wealth(self):
        config = SimulationConfig(pop_size=1, init_wealth=10, logistic_capacity=1,
                                  base_growth=0, gain_prob=1, gain_fraction=1,
                                  investment_risk=1, failed_investment_loss=1,
                                  loss_prob=0, tau_base=0, tau_max=0,
                                  birth_prob_max=0, death_base_prob=0, aging_risk_rate=0)
        sim = Simulation(config)
        sim.advance(2)
        self.assertEqual(sim.population[0].wealth, 0)
        self.assertEqual(sim.history[1]['Private investment losses'], 10)
        self.assertEqual(sim.history[2]['Private investment losses'], 0)
        self.assertEqual(sim.history[-1]['Gini coefficient'], 0)

    def test_healthcare_is_paid_from_the_government_budget(self):
        sim = Simulation(SimulationConfig(pop_size=10, healthcare_spending_fraction=0.25))
        sim.government_budget = 100
        sim.update_healthcare()
        self.assertEqual(sim.healthcare_spending, 25)
        self.assertEqual(sim.government_budget, 75)
        self.assertLess(sim.mortality_rate, sim.config.death_base_prob)

    def test_mortality_moves_gradually_and_recovers_without_funding(self):
        sim = Simulation(SimulationConfig(pop_size=10, healthcare_spending_fraction=1,
                                          healthcare_response_rate=0.25))
        original = sim.mortality_rate
        sim.government_budget = 100
        sim.update_healthcare()
        improved = sim.mortality_rate
        self.assertLess(improved, original)
        self.assertGreater(improved, original * sim.config.mortality_floor_fraction)
        sim.update_healthcare()  # Budget was exhausted; protection wears off.
        self.assertGreater(sim.mortality_rate, improved)
        self.assertLess(sim.mortality_rate, original)
        self.assertEqual(sim.healthcare_spending, 0)

    def test_healthcare_reduces_aging_risk_without_a_maximum_age(self):
        sim = Simulation(SimulationConfig(pop_size=10, healthcare_spending_fraction=1))
        sim.government_budget = 100
        sim.update_healthcare()
        self.assertGreater(sim.death_probability(80, 1), sim.death_probability(20, 1))
        self.assertLess(sim.death_probability(80, 1), sim.death_probability(80, 1, funded=False))
        for age in (100, 110, 120, 150, 10000):
            self.assertGreater(sim.death_probability(age, 1), 0)
            self.assertLess(sim.death_probability(age, 1), 1)
            self.assertLessEqual(sim.death_probability(age, 1), sim.death_probability(age, 1, funded=False))
        # Spending also improves age-related risk when baseline mortality is zero.
        zero_base = Simulation(replace(sim.config, death_base_prob=0))
        zero_base.government_budget = 100
        zero_base.update_healthcare()
        self.assertLess(zero_base.death_probability(80, 1), zero_base.death_probability(80, 1, funded=False))

    def test_zero_healthcare_reproduces_unfunded_age_risk(self):
        sim = Simulation(SimulationConfig(healthcare_spending_fraction=0))
        sim.government_budget = 100
        sim.update_healthcare()
        self.assertEqual(sim.government_budget, 100)
        self.assertEqual(sim.death_probability(80, 1), sim.death_probability(80, 1, funded=False))

    def test_pensions_are_equal_budget_limited_transfers_to_retirees(self):
        sim = Simulation(SimulationConfig(pop_size=3, init_wealth=10, retirement_age=65,
                                          pension_per_person=0.5, pension_budget_fraction=0.5))
        sim.population[0].age = 65
        sim.population[1].age = 70
        sim.population[2].age = 64
        sim.government_budget = 4
        sim.pay_pensions()
        self.assertEqual(sim.pension_spending, 2)
        self.assertEqual(sim.pension_shortfall, 8)
        self.assertEqual(sim.government_budget, 2)
        self.assertEqual([p.wealth for p in sim.population], [11, 11, 10])
        self.assertEqual([p.pension_received for p in sim.population], [1, 1, 0])

    def test_government_accounts_reconcile_every_spending_category(self):
        config = SimulationConfig(pop_size=3, init_wealth=10, base_growth=0, gain_prob=0,
                                  loss_prob=0, tau_base=0.2, tau_max=0.2,
                                  direct_redistribution_fraction=0.25, pension_budget_fraction=0.5,
                                  pension_per_person=0.3, healthcare_spending_fraction=0.25,
                                  investment_probability=1, birth_prob_max=0, death_base_prob=0,
                                  aging_risk_rate=0, healthcare_choice_mode="Public only")
        sim = Simulation(config)
        sim.population[0].age = 70
        sim.government_budget = 20
        sim.step()
        row = sim.history[-1]
        self.assertAlmostEqual(row['Tax revenue'], 6)
        self.assertAlmostEqual(row['UBI transfers'], 6.5)
        self.assertAlmostEqual(row['Pension spending'], 3)
        self.assertAlmostEqual(row['Healthcare spending'], 4.125)
        self.assertGreater(row['Capacity investment'], 0)
        self.assertAlmostEqual(row['Government balance error'], 0)
        expected = row['Opening government budget'] + row['Tax revenue'] + row['Estate revenue'] - row['Total government spending']
        self.assertAlmostEqual(expected, row['Government budget'])

    def test_private_premiums_transfer_wealth_to_providers(self):
        sim = Simulation(SimulationConfig(pop_size=1, init_wealth=10,
                                          healthcare_choice_mode="Private if affordable",
                                          private_healthcare_premium=0.1,
                                          private_healthcare_max_wealth_fraction=0.5))
        person = sim.population[0]
        person.age = 20
        sim.choose_healthcare()
        self.assertEqual(person.healthcare_choice, "Private")
        self.assertAlmostEqual(person.healthcare_premium, 1.2)
        self.assertAlmostEqual(person.wealth, 8.8)
        self.assertAlmostEqual(sim.private_healthcare_balance, 1.2)
        self.assertAlmostEqual(person.wealth + sim.private_healthcare_balance, 10)
        self.assertEqual(sim.government_budget, 0)
        self.assertEqual(sim.individual_death_probability(person), sim.private_death_probability(person.age, person.wealth))

    def test_adaptive_choice_depends_on_affordability_and_public_quality(self):
        sim = Simulation(SimulationConfig(pop_size=2, healthcare_choice_priority=10))
        poor, rich = sim.population
        poor.wealth, rich.wealth = 0.001, 10
        poor.age = rich.age = 80
        sim.choose_healthcare()
        self.assertEqual(poor.healthcare_choice, "Public")
        self.assertEqual(rich.healthcare_choice, "Private")
        self.assertEqual(poor.wealth, 0.001)
        # With stronger public protection than private care, adaptive agents stay public.
        sim.mortality_multiplier = 0.2
        wealth_before = rich.wealth
        sim.choose_healthcare()
        self.assertEqual(rich.healthcare_choice, "Public")
        self.assertEqual(rich.wealth, wealth_before)

    def test_estate_revenue_reconciles_after_extinction(self):
        sim = Simulation(SimulationConfig(pop_size=1, init_wealth=10, gain_prob=0,
                                          loss_prob=0, base_growth=0, tau_base=0, tau_max=0,
                                          healthcare_choice_mode="Public only", death_base_prob=1))
        sim.step()
        self.assertEqual(sim.history[-1]['Estate revenue'], 10)
        self.assertEqual(sim.government_budget, 10)
        self.assertAlmostEqual(sim.history[-1]['Government balance error'], 0)

    def test_live_policy_update_preserves_state_and_applies_next_step(self):
        sim = Simulation(SimulationConfig(pop_size=5))
        sim.advance(3)
        state = sim.result()
        rng_state = sim.rng.get_state()[1].copy()
        self.assertTrue(sim.update_policy(tau_base=0.01, healthcare_spending_fraction=0.5))
        self.assertEqual(sim.result(), state)
        self.assertTrue((sim.rng.get_state()[1] == rng_state).all())
        self.assertEqual(sim.policy_changes[-1]['Effective step'], 4)
        self.assertEqual(sim.initial_config.tau_base, SimulationConfig().tau_base)
        sim.step()
        self.assertGreater(sim.history[-1]['Tax revenue'], 0)

    def test_invalid_policy_is_atomic_and_initial_conditions_cannot_change(self):
        sim = Simulation()
        initial = sim.config
        for changes in ({'tau_base':0.9, 'tau_max':0.1}, {'healthcare_spending_fraction':-0.1},
                        {'pension_budget_fraction':float('nan')}, {'pop_size':10}):
            with self.assertRaises(ValueError):
                sim.update_policy(**changes)
            self.assertEqual(sim.config, initial)
            self.assertFalse(sim.policy_changes)

    def test_saved_simulation_without_policy_state_is_upgraded(self):
        sim = Simulation(SimulationConfig(pop_size=5), seed=7)
        sim.advance(3)
        expected = sim.result()
        population = sim.population
        rng = sim.rng
        del sim.policy_changes
        del sim.initial_config
        restored = restore_simulation(sim)
        self.assertEqual(restored.result(), expected)
        self.assertIs(restored.population, population)
        self.assertIs(restored.rng, rng)
        self.assertEqual(restored.step_count, 3)
        self.assertFalse(restored.policy_changes)
        restored.update_policy(tau_base=0.01)
        restored.advance()
        self.assertEqual(restored.step_count, 4)
        self.assertEqual(restored.policy_changes[-1]['Effective step'], 4)
        self.assertIs(restore_simulation(restored), restored)

    def test_ubi_is_equal_for_rich_poor_and_retired_people(self):
        sim = Simulation(SimulationConfig(pop_size=3, direct_redistribution_fraction=0.25))
        for person, wealth, age in zip(sim.population, [1, 100, 10], [10, 40, 80]):
            person.wealth, person.age = wealth, age
        sim.government_budget = 120
        sim.pay_ubi()
        self.assertEqual([p.ubi_received for p in sim.population], [10, 10, 10])
        self.assertEqual([p.wealth for p in sim.population], [11, 110, 20])
        self.assertEqual(sim.government_budget, 90)
        self.assertEqual(sim.ubi_spending, 30)
        self.assertEqual(sim.ubi_recipients, 3)
        sim.government_budget = 0
        sim.pay_ubi()
        self.assertTrue(all(p.ubi_received == 0 for p in sim.population))

    def test_progressive_tax_curve_matches_taxation_and_equal_wealth(self):
        config = SimulationConfig(tau_base=0.01, tau_max=0.05, tau_gamma=2)
        rates = wealth_tax_rates([10, 20, 30], config)
        self.assertAlmostEqual(rates[0], 0.01)
        self.assertAlmostEqual(rates[1], 0.02)
        self.assertAlmostEqual(rates[2], 0.05)
        self.assertEqual(list(wealth_tax_rates([10, 10, 10], config)), [0.01]*3)
        self.assertEqual(list(wealth_tax_rates([], config)), [])
        for actual, expected in zip(rates, tax_rates_at_relative_wealth([0, 0.5, 1], config)):
            self.assertAlmostEqual(actual, expected)

    def test_extinction_stops_cleanly(self):
        sim = Simulation(SimulationConfig(pop_size=1, death_base_prob=1, healthcare_choice_mode="Public only"))
        sim.advance(100)
        self.assertEqual(sim.step_count, 1)
        self.assertEqual(sim.population, [])
        self.assertEqual(sim.history[-1]['Gini coefficient'], 0)
        self.assertFalse(sim.step())

    def test_inheritance_uses_stable_parent_ids(self):
        sim = Simulation(SimulationConfig(pop_size=1, base_growth=0, gain_prob=0, loss_prob=0,
                                         tau_base=0, tau_max=0, birth_prob_max=0, death_base_prob=0,
                                         healthcare_choice_mode="Public only"))
        sim.population = [Individual(10, 99, person_id=40), Individual(5, 10, parent_id=40, person_id=90)]
        with patch.object(sim, 'individual_death_probability', side_effect=lambda p: float(p.person_id == 40)):
            sim.step()
        self.assertEqual(len(sim.population), 1)
        self.assertEqual(sim.population[0].wealth, 15)

    def test_human_mortality_profile_and_wealth_independence(self):
        sim = Simulation()
        risk = lambda age: sim.death_probability(age, 1, funded=False)
        self.assertGreater(risk(0), risk(1))
        self.assertGreater(risk(1), risk(10))
        self.assertLess(risk(20), 0.002)
        for age, lower, upper in ((0, 0.004, 0.007), (50, 0.002, 0.006),
                                   (60, 0.006, 0.015), (80, 0.04, 0.09), (100, 0.25, 0.5)):
            self.assertGreater(risk(age), lower)
            self.assertLess(risk(age), upper)
        self.assertTrue(all(risk(age + 1) > risk(age) for age in range(30, 120)))
        self.assertEqual(sim.death_probability(100, 0), sim.death_probability(100, 1e12))

    def test_infants_receive_a_mortality_draw_before_aging(self):
        sim = Simulation(SimulationConfig(pop_size=1, birth_prob_max=0))
        sim.population[0].age = 0
        ages = []
        def survive(person):
            ages.append(person.age)
            return 0
        with patch.object(sim, 'individual_death_probability', side_effect=survive):
            sim.step()
        self.assertEqual(ages, [0])
        self.assertEqual(sim.population[0].age, 1)

    def test_old_age_can_survive_and_doubling_time_is_validated(self):
        sim = Simulation(SimulationConfig(pop_size=1, birth_prob_max=0,
                                          death_base_prob=0, aging_risk_rate=0))
        sim.population[0].age = 150
        sim.step()
        self.assertEqual(sim.population[0].age, 151)
        with self.assertRaises(ValueError):
            sim.update_policy(mortality_doubling_years=0)
        with self.assertRaises(ValueError):
            sim.update_policy(max_age=100)


if __name__ == '__main__':
    unittest.main()
