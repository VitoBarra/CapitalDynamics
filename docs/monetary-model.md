# Monetary economy: accounting and assumptions

The app contains one experimental euro-denominated monetary model. There are
no alternate-model adapters, old-session migrations or alternate budget regimes.
Restart the app after updating; old sessions and removed Python APIs are not
supported. Load a comparison preset or create a scenario to explore alternatives.

## Currency and units

All deposits, monetary payments, debts, financial assets and nominal wealth
are euros (€ / EUR). Real net wealth is in year-0 euros. Capital is measured
in capital units and output/consumption/investment in goods per year, not euros.
The price index begins at 1, corresponding to €1 per real unit at year zero.
Chart tooltips and table/CSV headers distinguish these units; scenario JSON
declares EUR. Calculations retain fractional cents and round only for display.
Euro denomination does not make this an ECB or euro-area institutional model.

## Starting accounts

Defaults: 100 residents, €1 each, 200 real productive-capital units,
€100 producer money and €20 bank capital. Capital initially belongs
equally to residents. The price level starts at 1. Initial deposits total €200;
bank reserves are €220, so bank equity is €20. The fiat issuer has a matching
€220 reserve liability and negative equity. This explicitly offsets initial
financial endowments: consolidated sector net worth equals real capital at
current prices. These are illustrative settings, not estimates.

Each resident has deposits, real productive capital, bonds and loan obligations.
Net wealth = deposits + capital × price + bonds at market value − loan principal
− accrued unpaid loan interest. Real net wealth divides that balance by the
price level. A conventional bounded Gini is not reported when net wealth can
be negative. Sector net worth is shown separately; residents are not assigned
fictional shares of bank or public equity.

The production, healthcare and treasury sectors all have deposit accounts.
There is one commercial bank, no physical cash and no interbank market.

## Annual sequence

1. Depreciate capital. Potential goods output is the lesser of productive
   capacity and working-age residents × productivity. There is no wealth cap.
2. The producer pays available wages, limited by its deposits and the wage
   fraction of potential output at the current price. Workers are adults below
   retirement age; there is no separate job-matching market.
3. Service existing household loans: accrued interest first, then scheduled
   principal. Collect net wealth taxes, limited by liquid money. Uncollected
   tax is reported, not carried as tax arrears.
4. Issue any permitted fiat grant; pay mandatory bond service and attempt
   refinancing plus additional policy borrowing, subject to buyer willingness,
   bank constraints, exclusion and the debt ceiling. Proceeds and grants are
   financing, not taxes. Carry unpaid obligations forward.
5. Freeze the remaining treasury policy budget. Reserve four percentages
   for UBI, budget-limited pensions, healthcare and public investment.
6. Buy public investment goods; working adults request private investment
   and optional investment credit. Ration private investment goods and credit
   proportionally. Spending moves deposits to producers; purchased goods
   become real capital with configurable efficiency and private failure risk.
7. Households buy consumption goods, rationed proportionally if necessary.
   Consumption destroys goods, not money. Unused goods expire each year.
8. Adjust prices using desired nominal goods spending / output value. Price
   adjustment is gradual, bounded at −10% / +25% annually, with a positive
   numerical price floor. Recycle producer profits and healthcare income to
   households. Distribute a configurable fraction of excess bank equity,
   subject to capital, liquidity and money-cap limits.
9. Update healthcare quality using real funding. Residents may buy indexed
   private care. Draw deaths at current ages, settle estates, age survivors,
   and process births. Newborn deposits and capital come from parents.

Unclaimed estates received after allocations are available next year.
Public and private healthcare share an abstract service sector outside the
goods-capacity calculation; there are no separate medical workers or queues.

## Budget percentages

All funding percentages are edited **together** under government settings.
They must total at most 100%. Defaults are UBI 25%, pensions 20%, healthcare
25%, investment 15%, unallocated 15%. Debt service has no allocation control.

The denominator is **treasury money remaining after mandatory debt service**:
opening money + collected taxes + bond proceeds + fiat grants − debt payments.
Changing display/section order does not change allocations. Unused policy allocations
stay in treasury; they do not spill into another policy.

The allocation bar always includes unallocated funds. A second bar shows
**actual cash expenditure percentages**, with a different denominator: the
sum actually paid to the four policies. Tables show allocated, spent and unused amounts. Bond
principal repayment is a cash outflow here, not an operating expense.
Charts describe the last recorded year; policy changes apply next year.

## Bonds and government shortfalls

Debt service is senior to discretionary policies: accrued coupons first, then
matured principal, pro rata within each category. Unpaid coupons and matured
principal remain contractual debt; overdue principal continues accruing its
fixed coupon, while coupon arrears do not compound. Repeated payment attempts
within one year never accrue the same coupon twice.

When borrowing is enabled, the government seeks unresolved debt service plus
the additional policy borrowing target. Adults offer a configurable fraction
of deposits; the bank is offered a separate target share, subject to prudential
credit capacity. Both offers are reduced by `1 / (1 + risk aversion × spread)`.
Household purchases transfer deposits; bank purchases create treasury deposits.
Targets are not guaranteed financing.

The ceiling uses nominal principal plus accrued coupons. Matched issuance and
immediate redemption can refinance matured principal at the ceiling; such
earmarked proceeds cannot fund coupons or policies. Accruals can exceed the
ceiling because existing obligations are never forgiven by an issuance limit.

New bonds issue at par with a fixed coupon equal to reference yield plus
sovereign spread. The spread combines a baseline, debt / annual nominal output
(ratio capped at 10), overdue debt / total debt, and a default reputation
penalty; total spread is capped at 50 percentage points. Output is explicit
simulation state, not inferred by reading the history table. These are
illustrative scenario rules, not calibrated probabilities of default.

Existing bonds are valued by discounting remaining coupons and principal at
the current required yield. Arrears are separately discounted one period;
overdue claims use a one-year recovery horizon. Thus higher spreads lower
existing fixed-coupon prices without changing contractual debt or creating
money. There is no continuous secondary-market order book. Balance sheets
mirror market-valued creditor assets as market-valued government liabilities;
nominal obligations are reported separately and still must be paid.

The government controls include a confirmed **Sovereign default** action,
queued for the next simulated year (and cancellable before execution). It
repudiates all government bond principal and coupon arrears, not household
loans or deposits. Residents, producers and the bank lose their claims.
Bank capital may become negative, freezing credit without an automatic bailout.
Issuance is blocked in the default year and for the configured full subsequent
years (default three). Each default adds an 8-percentage-point reputation
penalty by default, recovering by 10% annually; it persists after exclusion.
Default events and nominal debt reconciliations are exported and displayed.

## Banking

Investment loans require **repayment income as well as collateral**. Annual
loan demand and actual origination share one quote containing eligibility,
affordability, productive/bond collateral and borrower-specific pricing.
Loans are also limited by demand, bank capital, reserve ratios and money caps.

Verified repayment income is the last completed year's cash income after
wealth tax, **before debt service**, excluding discretionary bank distributions.
This avoids deducting loan interest both from income and from commitments.
At startup only actual wages already paid minus wealth tax are observable.
Deposits, new loans, asset sales, inheritances and expected investment gains
do not establish recurring income.

Reduce verified income by the income stress fraction (default 20%), allow at
most the debt-service fraction (35%) of that amount, then deduct existing
scheduled principal, accrued arrears and interest stressed by an extra
2 percentage points. New principal is limited by the remaining amount divided
by `(1 / term + quoted rate + rate stress)`. This is a conservative constant-
principal first-payment test, not an annuity/mortgage formula. Existing loans
at next-year maturity use their full outstanding principal in commitments.

The score combines 0.5 × collateral leverage, 0.3 × stressed repayment burden
and 0.2 × default history, bounded to 0–1. History saturates at three defaulted
loans. New fixed interest is policy rate + base spread + maximum risk premium
(default 3 percentage points) × score. This is a transparent **heuristic, not
a probability of default**. Current arrears/missed payments and the default
cooldown (three years) exclude fresh borrowing.

Loans and bank-held government bonds have 100% risk weight. Loans create
equal deposits and liabilities: borrowing alone does not create net wealth.
Principal repayment destroys deposits and reduces the bank loan asset.
Interest payments reduce deposits and become bank equity; distributions
recreate deposits against equity. Unpaid interest accrues as a bank asset and
borrower liability. **Prudential equity** excludes unpaid household and sovereign
interest and bond gains above face, while recognizing bond price losses.
Only prudential equity can support new lending and bank distributions.
This is a conservative model convention, not full regulatory capital or IFRS 9.
Contracts keep their original fixed rate, risk premium, installments and maturity.

Consecutive annual missed payments or unpaid maturity balances trigger
resolution. Liquid cash and discounted collateral sales are collected before
writing off residual principal and interest. The default recovery discount is
25% from current capital prices / bond market value. Producer deposits limit
sales; selling capital changes ownership, not aggregate capital. A discounted
bond sale transfers the corresponding face-value claim, not the issuer's debt.
Multiple loans resolve in contract order and share the resident's finite
cash/collateral. There is no fictitious buyer or assumed full recovery.

Cash-based **Bank realized profit** equals collected household loan interest
plus coupons received on bank-held bonds, less written-off household loan
principal and bank-held bond principal losses. Principal repayments, loan issuance,
unpaid interest and distributions are not income in this measure.
Prudential equity changes by this profit minus distributions plus the separately
reported bank bond valuation change (release/increase of conservative markdowns).
Residual total debt write-offs include interest; principal losses are recorded
separately to avoid charging unrecognised cash interest as a cash loss.

A bank without positive prudential equity stops extending credit. Deposits remain recorded claims:
there is **no bailout, resolution scheme, deposit insurance or bank-run
simulation**. There are no consumption loans, competing banks or adjustable
loan rates. These are intentional first-version boundaries.

On death, liquid estate money and the same discounted, producer-funded sales of capital/bonds
settle debts before inheritance. Sales depend on producer liquidity; unsold
assets can pass to heirs/the state, while unrecovered debt is written off.
Only surviving children inherit. Government acquisition of its own bonds
cancels those bonds rather than creating cash revenue.

## Living standards and income

The annual living-standard cohort is frozen after income distributions and
care decisions but **before deaths, aging and births**. Year zero has no
annual observation. Closing population and surviving residents' snapshots
must not be used to recompute annual denominators.

- Personal cash disposable income = wages + UBI + pensions + producer/
  healthcare/bank distributions + household bond coupons − wealth tax
  actually paid − household loan interest actually paid. It excludes loan
  proceeds, asset sales, inheritance and revaluations; principal repayments
  are balance-sheet transactions, not income costs. Consumption and private
  premiums are spending, not income deductions.
- Report the median in current euros and in year-0 euros using that year's
  goods trading price, not the new closing price for next year's trading.
- Relative low-income share counts personal incomes strictly below 60% of a
  positive median. A non-positive median leaves the threshold/share undefined,
  rather than reporting an apparently reassuring zero poverty rate. The
  non-positive income share remains defined.
- Consumption spending and goods consumed per person use actual consumption
  flows and the same cohort. Investment and private medical premiums are not
  included in this goods-consumption measure.
- Pension replacement is median pensions for ages 65–74 divided by median
  positive production wages for ages 50–59. Missing cohorts/denominators give
  no observation. It is a cross-sectional cohort proxy, not an individual's
  retirement-income replacement rate.

There is no household pooling or modified-OECD equivalence scale, so personal
income and relative low-income shares are **not directly comparable** to
Eurostat household-equivalised income/poverty. See [official data research
and calibration plan](calibration.md) for sources, definitions and differences.
All credit stress limits, score weights and recovery assumptions remain
scenario parameters, not empirically estimated or EBA-prescribed constants.

## Money and prices

- **Base money:** bank reserves issued by the monetary authority.
- **Broad money:** all non-bank deposits, **including treasury and provider
  deposits**. This intentionally broad model convention is not a national
  statistical definition of M1/M2.
- **Issuance:** an explicit fiat grant to treasury, increasing reserves and
  deposits equally. It reduces issuer equity, not commercial-bank equity.
  It does not create capital or goods directly.
- **Optional cap:** 0 disables it. A base cap only limits issuance; it does
  not prevent bank deposit creation. A broad cap constrains issuance, bank
  lending, bank bond purchases and distributions. Caps below starting/current
  supply are rejected; balances are never arbitrarily clipped. A capped
  economy can still experience money destruction on repayment.

Prices respond to planned goods expenditure relative to available goods,
not mechanically to money supply. The policy rate affects new loan pricing
and consumption propensity. Inflation indexing of pension targets is optional;
private healthcare premiums are indexed. The issuer, unlike the commercial
bank, is not constrained by negative equity. There is no FX, external sector,
monetary-policy reaction function, fitted inflation equation or forecast claim.

## Reproducibility and checks

Presets cover no credit/printing, government bonds, individual credit, a fixed
broad ceiling, expandable credit, and monetary financing. They start fresh
with seed 42; subsequent interventions are recorded by effective year.

## Dashboard and settings

Playback provides **Start** before the
first year, **Pause** while running, and **Resume** afterwards. Single-year
advancement is available while paused. The two main actions align side by
side on desktop and stack on narrow screens.

Settings buttons open compact, borderless forms with paired fields. All five
budget percentages are edited together in one short grid; details of spent
and unused amounts are collapsed below the allocation bars. Major sections have
bordered containers, while settings forms stay borderless. Native widget defaults contain the active values
so opening settings after live refreshes does not reset the displayed rates
or allocations to their minima.

Scenarios default to **0% minimum and 60% maximum net wealth tax**, with
progressivity 2. These are illustrative, not estimated policy parameters.
Relative wealth maps the poorest tax-base endpoint to 0 and the
richest to 1 without a fixed currency threshold; equal wealth receives the
minimum rate. Rates are invariant to rescaling the wealth values.

The sidebar's **Display** tab controls percentile groups, individual wealth
visibility/log scale, and age bins/units. Individual wealth and percentile
shares use matching viridis colors. Negative net wealth is shown as signed
percentile totals, never clipped into a pie. The dashboard includes net wealth
Gini history, the active tax curve, actual applied tax rates, healthcare patient
choices and mortality trends. Population, percentile, contract and account data remain
available in detailed tables and downloads. The annual finance ledger records
opening treasury money, taxes, borrowing, issuance, estates, policy/debt-service
payments, closing money and reconciliation error, with a separate CSV download.

Production reporting also tracks failed private investments, capital added and
capital shortfall relative to full investment efficiency. A failure counts only
when goods were actually purchased. Shortfall is forgone new capital, not lost
money or destruction of existing household assets. Real household net wealth
and productive capacity share a trend chart, but capacity is not a wealth cap:
there is no wealth ceiling or independent random destruction of money.

## Comparable mortality observations

Before drawing deaths, compute three mean age-specific probabilities over
the same living residents: **Unfunded mortality** assumes no protection;
**Public care mortality** assumes everyone uses current public care;
**Expected mortality** uses each resident's actual selected public/private
care. All include background and age-specific hazards.
**Observed mortality** is actual deaths divided by the same cohort size.
These observations are frozen before deaths, survivor aging and births,
so changes in composition during the year cannot change the denominator
or recompute expected risks from only survivors. Year zero records initial
risks but has no observed mortality interval.

## Validation boundaries

Regression tests cover currency-scale-independent tax rates, the common
collateral rule, coherent cohort mortality, euro formatting/exports and
accounting identities under varied policy settings. Goods output equals
consumption plus investment plus unused goods; closing capital equals
depreciated opening capital plus public and private capital formation.
Consolidated sector net worth equals capital valued at current prices.

These checks establish internal consistency in the tested cases, not
empirical validity. Inflation, consumption, credit demand and healthcare
benefits are illustrative rules, not fitted causal relationships. Healthcare
has no medical staffing, queues or capacity constraints. Predictive policy
use would require data calibration, out-of-sample validation and sensitivity
analysis; changing the currency label cannot provide that validation.

Tests check matching assets/liabilities, money creation/destruction, sector
consolidation, government reconciliation, defaults, estate settlement, caps,
resumption, UI controls and live fragment refreshes. Downloads include sector
balances, household accounts, contracts, retained history and a bounded
transaction ledger. Settings are a reproducibility description, not a full
state checkpoint. History retains 10,000 years, transactions 10,000 entries,
and policy history 1,000 interventions. A complete replay also requires any
interventions no longer present in the retained policy history.
