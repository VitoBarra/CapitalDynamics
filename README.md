# Capital Dynamics

Capital Dynamics is an interactive simulator for exploring wealth and population in a simplified capitalist economy. Individuals hold private wealth, experience growth and random gains or losses, pay wealth-based taxes, and pass wealth to their children. Public policy and demographic changes influence how that wealth evolves.

## Getting started

You need Python 3.10 or newer, `make`, and an internet connection to install dependencies. From the project directory, run:

```bash
make run
```

This creates a `.venv` virtual environment, installs dependencies, and starts the Streamlit app. Open the local URL shown in the terminal. Stop the server with `Ctrl+C`.

Use `make install` to install dependencies without launching the app, `make test` to run the model and interface checks, or `make help` to list commands.

### Local launch settings

Run `make init-env` to create a Git-ignored `.env.local` prefilled with all available launch settings and their defaults. Existing settings are never overwritten. The Makefile reads this file automatically when present; it is optional.

Add any settings you want to override, using Makefile-style assignments (without shell quotes):

```makefile
PORT=8502
HOST=127.0.0.1
HEADLESS=true
STREAMLIT_ARGS=--server.runOnSave=true
```

Available settings are `PORT` (default `8501`), `HOST` (`localhost`), `HEADLESS` (`false`), `APP` (`app.py`), `PYTHON` (`python3`), `VENV` (`.venv`), and `STREAMLIT_ARGS` (empty). Variables are also exported to launched processes, so additional Streamlit settings such as `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false` can be added. Explicit launch flags take precedence over equivalent Streamlit environment variables.

Command-line overrides take priority over `.env.local`, for example `make run PORT=8503`. Plain `make` still launches the app.

## Run a scenario

The simulator starts with 100 people, one wealth unit each, and capacity for 200 wealth units. Defaults favor moderate growth, a functioning public budget and slower demographic change. They are exploratory model settings, not estimates for a real economy. Existing sessions keep their parameters; the sidebar's **Load default scenario** button starts a fresh run with the revised defaults.

- **Batch:** choose how many steps to advance and select **Advance simulation**. Repeating this continues the same economy.
- **Live:** select **Start / resume** to advance continuously without a step limit. Adjust the refresh interval and steps per refresh to change playback speed. **Pause** freezes the economy for inspection; **Single step** advances it once while paused. Live updates run while the session is open.
- **Reset current scenario:** return to step zero with the current scenario's parameters and random seed.
- **Create new scenario:** use the sidebar for initial population, initial wealth, initial capacity and random seed. This creates an economy at step zero using the currently active policies.

Policy parameters are next to the charts they affect. Open an **Edit…** button, adjust values, and select **Apply policy**. Changes take effect on the next step without resetting population, wealth, history, healthcare protection or the random sequence. Live mode keeps running. While paused, changes wait until you advance again. Controls stay outside the timed chart refresh so automatic updates do not interrupt parameter edits. Invalid tax ranges are rejected as one transaction.

| Section | Live controls |
| --- | --- |
| Current wealth distribution | Private opportunity probabilities, gains, investment risk and random losses. |
| Economy over time | Growth, wealth growth effect, capacity depreciation and public investment. |
| Government spending and UBI | Tax rates, progressivity, Universal Basic Income (UBI), pension eligibility and pension funding. |
| Healthcare, aging and mortality | Public healthcare funding and effectiveness; private premiums, quality, affordability and personal choice. |
| Population age distribution | Births, background mortality, adult reference hazard and mortality doubling time. No maximum age. |

Changing display settings also preserves the scenario. Each session has its own population and random sequence. Identical initial parameters, random seeds, and policy interventions at the same simulation steps produce identical results, including when a run is paused and resumed. The latest 1,000 policy changes are retained with their effective steps and included in the scenario settings download, together with initial and current parameters.

Live mode stops if the population becomes extinct. It retains the latest 10,000 history rows to bound history storage; this does not limit the number of simulation steps. Trend charts show the selected window within those retained rows.

## Dashboard

All seven views from the original Matplotlib animation are available, alongside healthcare and mortality charts:

| View | Details |
| --- | --- |
| Individual wealth | One bar per person, sorted from poorest to richest; percentile colors match the pie chart. Hover for person ID, rank, wealth and age; zoom to inspect a range. Optional logarithmic scale. |
| Wealth distribution pie | Wealth shares by population percentile, with configurable group count, percentage labels and precise hover values. Rank-based groups also handle equal wealth. |
| Total wealth and capacity | Private wealth and the changing wealth capacity on the same time axis, plus the original dashed horizontal reference at the current capacity. |
| Population history | Population at each recorded step. |
| Government budget | Unspent public funds over time. |
| Gini history | Inequality on a fixed zero-to-one scale. |
| Age distribution | Configurable age bins, displayed as population shares or counts. |
| Mortality history | Unfunded baseline, current healthcare-adjusted baseline and observed deaths as a share of the population. |
| Tax policy | Active tax curve, projected personal tax rates and actual applied rates over time. |
| Government spending | Stacked expenditure history and the latest breakdown across UBI, pensions, public healthcare and capacity investment. |
| Healthcare spending | Public healthcare expenditure per step. |
| Healthcare choices | Public and private patient counts per step, alongside private premium revenue and accumulated provider assets. |
| Death risk by age | Public, private and unfunded mortality curves; private risk includes the reduction in personal wealth from its premium. |

The summary cards show current population, personal wealth, government budget and Gini coefficient. The Gini coefficient is zero for equal wealth and approaches one as wealth concentrates.

Under **Detailed data and downloads**, inspect individual wealth, age, parent IDs, UBI receipts, pension receipts, healthcare choice, premium and death probability alongside precise percentile shares. Download a population snapshot, finance ledger, retained time series, or scenario parameters. Step zero is included in the history.

## Default scenario

| Parameter | Default | Purpose |
| --- | --- | --- |
| Population / wealth / capacity | 100 / 1 per person / 200 | A small population with room for growth. |
| Base growth / wealth effect | 4% / alpha 0 | Moderate growth without the previous negative-alpha singularity. |
| Wealth taxes per step | 0.5% minimum, 4% maximum, gamma 2 | A public revenue stream even when wealth is equal; these are wealth taxes, not income tax rates. |
| UBI allocation | 25% of available government funds | Equal transfers with funds left for pensions, care and investment. |
| Pensions | Age 65; target 0.02 wealth units; up to 20% of remaining funds | Budget-limited pension payments. |
| Public healthcare | 25% of remaining funds; effectiveness 10 | Material funding with gradual effects. |
| Private opportunities | 25% event chance; 15% of people; 10% gain | Moderate opportunity-driven variation. |
| Private investment risk | 15% chance of losing 10% of wealth | Downside risk without the former large losses. |
| Independent losses | 15% event chance; 10% of people; up to 10% loss | Less abrupt private wealth destruction. |
| Public investment / depreciation | 20% event chance / 0.05% capacity loss | Slower capacity erosion. |
| Birth peak / background mortality / adult reference hazard | 3% / 0.02% / 0.003 at age 50 | Random annual deaths; adult hazard doubles every 7 years, with no lifespan cutoff. |
| Private premium / mortality factor | 0.008 initial wealth / 0.5 | Paid health benefits with an affordability tradeoff. |

Earlier sensitivity checks used the former linear mortality model and maximum-age cutoff; they do not validate population stability under the new mortality profile. Birth rates and economic defaults remain exploratory rather than a demographic forecast.

The wealth tax graph shows `minimum + (maximum - minimum) × relative_wealth ** gamma`. Relative wealth runs from the poorest person's wealth (0) to the richest (1), rather than population percentiles. Equal wealth pays the minimum. The curve uses the active policy; dots project rates on current wealth. The applied-rate chart records the actual minimum, maximum and revenue-weighted effective rate from taxation each step. Policy changes update the curve immediately and affect collections on the next step.

## Model settings

Current model parameters are available in grouped controls:

| Group | Parameters |
| --- | --- |
| Starting economy | Population, initial wealth, wealth capacity, base growth, wealth-dependent growth effect (`alpha`). |
| Taxes and redistribution | Minimum and maximum wealth tax rates, progressivity (`gamma`), fraction of available government funds paid equally as UBI each step. |
| Private investment risk and random losses | Opportunity event probability, affected population fraction, successful gain rate, failure probability, wealth fraction lost on failure, and independent random loss settings. |
| Public investment | Investment probability, capacity depreciation (`delta`), return exponent (`beta`), base efficiency, random shock magnitude, failed investment damage and success sensitivity (`psi`). |
| Pensions and UBI | Retirement eligibility age, pension budget fraction, desired pension per retiree in multiples of initial wealth. |
| Private healthcare | Choice strategy, premium, age surcharge, mortality risk factor, affordability limit and health-versus-wealth preference. |
| Healthcare and aging | Share of remaining public funds spent on healthcare, effectiveness, adjustment speed and minimum mortality hazard fraction. |
| Demographics | Maximum birth probability, background death probability, adult reference age and hazard, mortality doubling time. |
| Display | Percentile groups (originally `tick_count`), age bins and units, history window, individual wealth visibility and logarithmic scale. |

## Step mechanics and assumptions

Each step applies wealth growth and private opportunities or random losses, collects wealth taxes, redistributes UBI, pays pensions, funds public healthcare, lets people choose public or private care, potentially invests remaining public funds in capacity, and processes deaths over the current age-year. Survivors age by one year, then births are processed. Newborns receive their first infant mortality draw on the following step.

Growth is limited by `max(1 - total personal wealth / capacity, 0)`. An individual's growth multiplier is `1 / max(1 + alpha × wealth, 0.01)`, so negative alpha favors wealthier people. The denominator floor prevents a singularity. Private opportunities are sampled with wealth-based weights. Each selected person independently succeeds or fails: success adds `wealth × gain_growth × global_growth_factor`; failure removes `wealth × failed_investment_loss`. Failure can lose wealth even when capacity limits growth. A failure probability of zero restores gain-only opportunities; one makes every selected opportunity fail. These failures are separate from the existing random loss events, which favor poorer people. The dashboard reports private opportunity failures, gains and losses for the latest step, and the history CSV includes them for every retained step. Tax rates depend on relative wealth and progressivity. UBI pays every resident the same amount, regardless of wealth, age or healthcare choice. Public investment can expand capacity or damage it when it fails; capacity also depreciates.

### Government accounts, UBI and pensions

The government now records its opening budget, tax receipts, unclaimed estates, UBI transfers, pension payments, public healthcare spending, capacity investment and closing balance. Every step reconciles:

```text
closing budget = opening budget + taxes + estates
                 - UBI - pensions - public healthcare - capacity investment
```

Allocations use the remaining budget in that order. Fractions are sequential, rather than percentages of one shared original budget. The government does not borrow. Estate revenue arrives after spending and is available for the next step. The dashboard shows the expenditure mix over time, the latest breakdown, and an account reconciliation; the finance CSV includes all retained steps.

Universal Basic Income (UBI) replaces the earlier inverse-wealth redistribution. Each step, 25% of available government funds is divided equally among all current residents, including children and retirees. The amount is deducted from the government budget and added to each person's wealth. With no public funds, the payment is zero; no money is created or borrowed. It is a variable budget-funded payment rather than a fixed guaranteed entitlement. Historical transfer totals from older sessions keep their amounts when renamed; old per-person receipts cannot be reconstructed. Pensions add an age-based payment: people aged 65 and above qualify by default, regardless of wealth. Desired pensions are 0.02 times initial wealth per retiree per step, funded with at most 20% of the funds remaining after UBI. If the budget is insufficient, every retiree receives the same reduced payment; unmet entitlement is reported as a shortfall and is not carried as debt. Without retirees, pension funds remain available for later uses. Pension transfers increase personal wealth before healthcare choices. Retirees can receive both UBI and pensions.

### Private healthcare and personal decisions

Public healthcare remains available to everyone. Each step, people can instead buy private care using their own wealth. The default premium is 0.008 times initial wealth per person, increased by an age surcharge:

```text
premium = initial wealth × premium rate × (1 + age surcharge × age / 100)
```

Private care replaces the public mortality hazard multiplier with a configurable private factor (0.5 by default). Neither system imposes a maximum age. The premium's 100-year denominator is a fixed price reference, not a lifespan limit. Premiums reduce personal wealth and affect affordability and future investments; wealth does not directly suppress biological aging.

The **Adaptive** strategy compares each person's public death risk with private death risk after paying the premium. It buys private care only if the premium is affordable and:

```text
(public risk - private risk) × health priority × personal preference > premium / personal wealth
```

Personal preference varies between 0.5 and 1.5 and remains attached to the person. Age affects both the risk reduction and the premium. By default, a person will spend at most 20% of their wealth on a private premium. Wealthier people can afford more, older people may value a greater risk reduction, and improved public care can make private care less attractive. People reassess every step. **Public only** and **Private if affordable** let you compare alternative decision rules; unaffordable private care always falls back to public care.

Premiums become assets of an aggregate private healthcare provider sector. They do not disappear from the private economy and are not included in government spending. The personal wealth charts and inequality calculation cover individuals; total private sector wealth adds provider assets. This simplified provider sector accumulates fees without modeling staff, operating costs, ownership, taxation or reinvestment.

### Healthcare, mortality and aging

By default, 25% of the government budget remaining after UBI and pensions is spent on healthcare each step, before capacity investment. The payment leaves the government budget. Spending per person is divided by initial wealth per person so effects scale with the scenario's wealth units.

Healthcare creates a target mortality multiplier:

```text
funding = healthcare spending / population / initial wealth per person
target = floor + (1 - floor) / (1 + effectiveness × funding)
multiplier += adjustment speed × (target - multiplier)
```

The multiplier starts at one. Sustained spending lowers it gradually; reduced or zero funding moves it back toward one. The default floor of 0.2 allows up to an 80% reduction in mortality **hazard**, not necessarily annual probability. A zero healthcare allocation recovers the unfunded model after any existing protection fades.

Every person receives an independent Bernoulli death draw each year. The annual hazard is converted to a probability, rather than clipped at a maximum age:

```text
adult = aging_risk_rate × exp(log(2) × (age - aging_risk_start) / mortality_doubling_years)
infant = aging_risk_rate × 1.8 × exp(-2 × age)
young_adult = aging_risk_rate × 0.3 × exp(-0.5 × ((age - 25) / 10)^2)
hazard = -log(1 - death_base_prob) + adult + infant + young_adult
death probability = 1 - exp(-hazard × healthcare multiplier)
```

`aging_risk_start` is now a **reference age**, not a threshold: the adult component exists on either side of age 50. At default settings, unfunded annual risks are approximately 0.56% in infancy, 0.12% at 20, 0.32% at 50, 0.82% at 60, 5.7% at 80 and 34.6% at 100. Death becomes increasingly likely but is never forced by age; a numerical guard keeps finite-age probabilities below one. Setting background mortality to one explicitly forces death for stress testing. Setting both background mortality and the reference hazard to zero disables mortality.

The Gompertz-style adult curve, infant excess and young-adult hump approximate the shape and scale in the [SSA 2022 period life table](https://www.ssa.gov/oact/STATS/table4c6_2022_TR2025.html). It is a modern US reference, not a universal human table or an exact fit; the model has no sex-specific mortality. For comparison, that table reports age-60 risks of 0.77–1.25% and age-100 risks of 34.3–39.2% across females and males. Very-old-age extrapolation is uncertain.

[Our World in Data describes the J-shaped age profile and its historical changes](https://ourworldindata.org/how-do-the-risks-of-death-change-as-people-age). Mortality has fallen at all ages, not just in childhood: [French data](https://ourworldindata.org/data-insights/death-rates-have-declined-across-all-ages) show roughly 50-fold lower infant mortality and five-fold lower mortality at 65 between 1816 and 2021. Improvements differ by age, country and era and can reverse during crises. Consequently, the simulator does **not** assume an automatic, indefinite annual improvement. Survival changes over simulation time through healthcare funding, its lagged protection and individual public/private choices. The uniform healthcare multiplier and its spending response are illustrative policy assumptions, not causal estimates inferred from these historical trends. The existing baseline chart tracks the background component only; the age-risk chart shows the full model.

### Births and inheritance

Birth probability depends on age, is nonzero at ages 14–68, and peaks at age 30. A parent transfers half their wealth when a child is born. On death, wealth passes to children in the population, or to the government when there are none. Stable person IDs preserve family links as the population changes.

This is an exploratory toy model, not a forecast or a complete representation of capitalism. It does not currently model firms, wages, prices, trade, debt, or markets. For age and mortality, a step is one year; economic rates remain illustrative per-step settings.

## Project files

- `app.py`: Streamlit controls, playback and interactive charts.
- `simulation.py`: Stateful model shared by batch and live runs.
- `policy_controls.py`: Section-local policy forms and live policy submission.
- `PopolationEconomicSimulation.py`: Original Matplotlib animation, retained as a reference. Its Matplotlib dependency is separate from the Streamlit app's requirements.
- `tests/`: Model and interface regression checks.
