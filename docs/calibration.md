# Official data research and calibration plan

Source snapshot: **19 November 2026**. These observations are references, not
fitted defaults, forecasts or a claim that the sandbox represents a particular
country. No live data calls occur during simulation. The same references are
available under **Living standards and income → Official data references and
calibration status** and in `capital_dynamics/calibration.py`.

## Verified observations and definitions

| Quantity | Observation | Coverage and period | Official source |
| --- | --- | --- | --- |
| Median equivalised disposable income | **€22,939/year** | EU27; EU-SILC 2025, generally income reference year 2024 | [Eurostat `ilc_di03`](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_di03?geo=EU27_2020&time=2025&age=TOTAL&sex=T&statinfo=MED_EI&unit=EUR) |
| Relative income-poverty threshold | **60% of national median equivalised disposable income** | EU-SILC definition | [Eurostat methodology](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Living_conditions_in_Europe_-_income_distribution_and_income_inequality) |
| Aggregate pension replacement ratio | **0.60, or 60%** | EU27; total sex; EU-SILC 2025. Median gross individual pensions ages 65–74 / median gross individual earnings ages 50–59 | [Eurostat `ilc_pnp3`](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_pnp3?geo=EU27_2020&time=2025&sex=T) |
| New lending to sole proprietors and unincorporated partnerships | **4.36% annual agreed rate** | Euro area, September 2026; floating/fixation up to one year; release 2 November 2026 | [ECB bank interest statistics](https://www.ecb.europa.eu/press/stats/mfi/html/ecb.mir2611~2502265512.en.html) |
| Joint household assets, debt, income and consumption | HFCS 2023 wave, October 2026 statistical tables | Euro-area household distributions; mostly 2023, country reference dates differ (2022–2025) | [ECB HFCS tables](https://www.ecb.europa.eu/home/pdf/research/hfcn/HFCS_Statistical_Tables_Wave_2023_October_2026.pdf), [survey and access](https://www.ecb.europa.eu/stats/ecb_surveys/hfcs/html/index.en.html) |

The two numeric Eurostat API responses were checked directly. Their data
updates were dated 20 October 2026. Downloaded revisions can change values;
keep the period, selection and retrieval date with any future calibration.

**Important mapping restrictions**

- €22,939 is an **annual household-equivalised income**, not a household
  deposit balance, a per-person starting deposit, a gross wage or PPS.
  Euros and purchasing-power standards must not be interchanged.
- Eurostat uses the modified OECD household scale: 1 for the first adult,
  0.5 for additional people aged 14+, 0.3 for younger children. The model has
  individual residents, not observed household membership or income pooling.
  Its current relative low-income share is explicitly a personal-income
  **proxy**, not a directly comparable Eurostat poverty rate.
- The model's pension ratio uses the corresponding age bands, but its
  earnings denominator contains only positive production wages. It lacks
  complete employment earnings and household survey weights. Do not treat
  it as an exact replication or an individual's lifetime replacement rate.
- HFCS wealth and deposit statistics describe **households**, often
  conditional on owning an asset. Do not assign the household median to
  every resident or interpret a median as an aggregate average.
- The ECB lending rate describes a different fixation period and a real
  lending population. It is a relevant benchmark, not a fitted ten-year
  fixed-rate investment-loan parameter or a measured risk premium.
- EU27 and euro-area aggregates, survey reference years and current
  interest-rate observations are not one internally matched calibration
  dataset. Choose a geography and common base year before combining them.

## Creditworthiness principles used now

[EBA Guidelines on loan origination and monitoring](https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring)
(EBA/GL/2020/06, application from 30 June 2021), paragraphs **95–97** and
**119–120**, emphasise repayment capacity and sustainable income; collateral
is a secondary source of repayment and is not sufficient justification for
approval.

The model therefore now:

1. Checks observed income after wealth tax, **before debt service**, excluding
   discretionary bank distributions. At startup only actual wages already
   paid minus tax are available. Deposits, borrowing and expected capital
   returns cannot substitute for income.
2. Reduces income by a configurable stress fraction, limits total stressed
   debt service, and deducts existing debt commitments before sizing new debt.
3. Applies an explicit borrower risk premium and blocks new credit while in
   arrears or during a post-default exclusion period.
4. Sells collateral to a liquidity-constrained producer at a configurable
   discount, then writes off unrecovered principal/interest.
5. Separates book equity from a conservative capital measure excluding
   uncollected household interest. Only the latter supports credit and bank
   distributions. Cash-based profit excludes unpaid interest.

The **35% debt-service ceiling, 20% income reduction, +2 percentage point rate
stress, 25% liquidation discount, three-year exclusion period and score
weights are model assumptions**. EBA does not prescribe those values here.
The 0–1 score is not an estimated default probability. Annual missed-payment
counts do not implement a literal 90-days-past-due default rule.
This is not a full IFRS 9 expected-loss, non-accrual or regulatory-capital model.

## Further official datasets located

- [Eurostat `demo_mlifetable`: life tables by age and sex](https://ec.europa.eu/eurostat/databrowser/view/demo_mlifetable/default/table)
  for mortality calibration. Use annual death probabilities (`qx`) or
  explicitly convert hazards/rates, not life expectancy as a death chance.
  Observed life tables **already reflect healthcare**; treating them as an
  unfunded baseline and applying a full healthcare benefit again double-counts
  protection.
- [Eurostat `demo_frate`: fertility rates by age](https://ec.europa.eu/eurostat/databrowser/view/demo_frate/default/table)
  for births. Rates are defined for a female population and particular age
  denominators; the model currently draws births for all residents. A sex/
  fertility eligibility model is needed before direct substitution.
- [Eurostat `hlth_sha11_hf`: healthcare expenditure by financing scheme](https://ec.europa.eu/eurostat/databrowser/view/hlth_sha11_hf/default/table)
  for public/private spending levels in euros per inhabitant and spending/GDP
  shares. These are not shares of the model's **treasury budget**, nor causal
  estimates of how spending reduces mortality.

## Next implementation steps for a genuinely data-informed preset

1. Select a national or euro-area geography, base year and household unit.
   Obtain consistent income, consumption, assets, debt and age distributions,
   retaining weights, missing-data flags and uncertainty.
2. Introduce household membership/pooling and initialise **joint**
   distributions. Matching separate marginal medians is not enough.
3. Set real production, prices, wages, consumption and opening balance sheets
   together. Merely replacing €1 deposits with annual income would distort
   every stock/flow ratio.
4. Fit or benchmark lending spreads, debt-service burdens, default frequency
   and **loss given default**. Validate recovery discounts and rejection
   rates separately; do not infer them from aggregate interest rates alone.
5. Fit demographic risks with the correct denominators, and retain healthcare
   effects as assumptions until supported by causal evidence.
6. Validate income/consumption distributions, poverty/pension proxies and
   credit outcomes across many seeds and held-out periods. Publish sensitivity
   ranges and calibration errors rather than claiming accuracy from one run.

No defaults were silently changed to these empirical targets. The implemented
60% low-income convention and age-band pension comparison are measurement
definitions; full empirical calibration remains separate work.
