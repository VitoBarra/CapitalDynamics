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

Five goods firms start with separate zero deposit balances. In year one,
80% of the initial production holding-sector money funds them equally; 20%
remains with the holding/collateral dealer. This is a transfer, not additional
money. Starting inventory is zero. Firm cash and inventory are separate sector
assets; household net wealth does not include fictitious firm equity shares.
After production, consolidated net worth includes productive capital **and**
inventories, each valued at current prices.

The production holding sector, firms, healthcare, education, primary energy and treasury have deposit accounts.
There is one commercial bank, no physical cash and no interbank market.

## Annual sequence

1. Advance the technology frontier, draw discoveries using last year's funded
   research, and diffuse technology to firms. Depreciate productive capital.
2. Enroll school/university participants and pay teachers from opening education
   deposits before firms recruit. Apply inventory spoilage, fund replacement entry, bargain firm
   wages and forecast production from sales expectations and inventories.
   Firms reserve primary energy pro rata, then hire available residents within
   combined payroll/energy funding and credit limits. Produce within energy,
   leased-capital and adopted-productivity limits, paying ordinary wages,
   energy inputs and any funded research services.
3. Service existing household loans: accrued interest first, then scheduled
   principal. Collect net wealth taxes, limited by liquid money. Uncollected
   tax is reported, not carried as tax arrears.
4. Issue any permitted fiat grant; pay mandatory bond service and attempt
   refinancing plus additional policy borrowing, subject to buyer willingness,
   bank constraints, exclusion and the debt ceiling. Proceeds and grants are
   financing, not taxes. Carry unpaid obligations forward.
5. Freeze the remaining treasury policy budget. Reserve five percentages
   for UBI, budget-limited pensions, healthcare, public investment and education.
6. Buy public investment goods; working adults request private investment
   and optional investment credit. Ration private investment goods and credit
   proportionally. Spending moves deposits to producers; purchased goods
   become real capital with configurable efficiency and private failure risk.
7. Households buy consumption goods, rationed proportionally if necessary.
   Consumption destroys goods, not money. The education provider then buys
   available materials and advances study, training and work learning after production.
   Unsold goods remain firm inventory.
8. Service business debt, resolve failed firms, update firm prices using their
   own demand and unit costs, and calculate the fixed-opening-weight price index.
   Individual quote changes are bounded at −10% / +25% annually with a positive
   numerical floor. Recycle positive firm cash profits, energy resource income and healthcare income to
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
25%, investment 15%, education 10%, unallocated 5%. Debt service has no allocation control.

The denominator is **treasury money remaining after mandatory debt service**:
opening money + collected taxes + bond proceeds + fiat grants − debt payments.
Changing display/section order does not change allocations. Unused policy allocations
stay in treasury; they do not spill into another policy.

The allocation bar always includes unallocated funds. A second bar shows
**actual cash expenditure percentages**, with a different denominator: the
sum actually paid to the five policies. Tables show allocated, spent and unused amounts. Bond
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

## Competing firms, inventories and demand

Firms have independent cash accounts, prices, productivity, sales forecasts,
wage offers, inventories and debt. Initial efficiency is drawn uniformly
between 0.85 and 1.15 by default, using a separate seeded firm RNG.

Expected startup sales total 65% of initial capital/labor potential. Forecasts
then adjust 40% toward current desired unit purchases each year. Planned output
is `max(0, expected sales × (1 + inventory target) − usable inventory)`.
The default inventory buffer is 15%; opening stock loses 10% to spoilage.
Firms therefore cut production/hiring after weak sales or excess inventories,
rather than producing at full capacity indefinitely.

Existing household/public/holding capital is operated under cost-free leases,
not duplicated on firm balance sheets. Capacity-use weights are 20% equal
access plus 80% expected-sales share. Total actual production cannot exceed
physical capacity or output supported by hired labor.

Goods buyers choose identical price-weighted baskets, with nominal purchase
weights proportional to `price ** -price_competition` (default exponent 2).
Stockouts redirect remaining budgets to stocked firms. Buyers in a batch share
rationing proportionally; public investment precedes private investment, then
consumption. Actual units are summed at individual transaction quotes, **not**
computed by dividing total money spent by the aggregate price index.

The annual physical identity is:

`opening inventories + production = consumption + investment + education goods + closing
inventories + spoilage + failure scrapping`.

Inventories are marked to each firm's quote, not bank deposits or productive
capital. CSV history includes a physical inventory reconciliation. This is
illustrative current-price accounting, not inventory-at-historical-cost IFRS.

## Employment and wage bargaining

The labor force is every resident aged 18 to retirement age except full-time
university students. Funded education jobs recruit first; firms hire integer
numbers of workers to meet planned production, subject to wage funding; higher
wage offers recruit first with seeded tie-breaking. Each resident has at most
one employer (goods firm or education provider). Unhired residents have no job wages but can receive
UBI, property income and healthcare income. Employment statistics are frozen
before demographics and describe goods/education jobs, not survey unemployment.
There is no separate healthcare labor market or explicit part-time hours.

The initial wage is base productivity × wage fraction. Subsequent wage growth
combines 50% of lagged inflation, 50% of the firm's adopted productivity gain,
and `0.1 × (6% reference unemployment − last unemployment)` by default.
Annual wage changes are bounded at −10% / +20%. The unemployment reference is
not an enforced employment rate. Changing the wage fraction scales current
offers without resetting technology or jobs/history.

## Firm prices and inflation

Each firm targets the larger of its excess-demand-adjusted quote and unit
payroll/research/energy cost × (1 + markup). Markup defaults to 10%. Quote changes
are bounded at −10% / +25%. No positive inflation floor is imposed.

The aggregate index chains weighted **price relatives**, using fixed
opening-year capacity-planning weights. Changing market shares or a firm's
exit alone therefore cannot mechanically generate inflation. It is a model
goods-price index, not a calibrated CPI or observed average transaction price.

Demand coverage divides desired nominal consumption/investment by all goods
offered at firm transaction quotes, including usable opening inventory.
It is undefined without supply; old stocks can be sold even with zero new
output. Coverage is a diagnostic, not an exact aggregate inflation formula
because firms also react to costs and their individual demand.

Demand-responsive production removes the previous forced-full-output bias.
It does **not** guarantee stable or positive inflation: saving, retained firm
cash, treasury balances, unemployment and credit constraints can still weaken
spending. More technology without more demand can reduce labor demand.
There is still no central-bank inflation target or expectations mechanism.

## Productivity growth and technology

Frontier worker productivity is base productivity × the technology index.
The index starts at 1 and advances before each year's production by
`(1 + productivity_growth) × (1 + breakthrough_gain)`. Default gradual growth
is 1% annually. A separate seeded random stream draws at most one economy-wide
breakthrough each year, with default probability 5% and a uniformly drawn
permanent productivity gain between 2% and 10%. A 5% chance means a 20-year
expected waiting time, not an event every 20 years.

Firms adopt the frontier gradually, closing 20% of their technology gap
annually by default, in addition to trend learning. Actual productivity is
base productivity × firm efficiency × adopted technology.

Firms spend 3% of post-payroll cash on research employee services by default.
This is paid household income and a firm expense, not a capitalized magic asset.
Next year's research intensity is paid research / max(sales, initial household
money). Firm discovery probability is `min(1, 2 × intensity)`; extra adoption
speed is `2 × intensity`, with total speed capped at 100%. A firm innovator
uses its discovery immediately, while rivals catch up gradually.
Several firms can innovate in one year in addition to the exogenous discovery.
Research services have a cash cost but no separately modeled hours or patents.

Growth and breakthrough settings can change during a run. Changing base
productivity preserves accumulated technology. Disable trend growth, exogenous
breakthroughs and research-led breakthroughs to freeze the frontier rather
than reset it. Existing adoption gaps can still close; a new scenario resets all.

The dashboard reports effective productivity, the technology index, annual
growth and breakthrough counts. Retained history/CSV includes event-year
indicators and gains; the scenario JSON also includes the index, total count
and retained event list. Technology events retain up to the history limit.
The independent technology RNG avoids shifting demographic/investment random
draws merely because innovations are enabled; economic effects can still
indirectly change subsequent outcomes.

## Primary energy and supply shocks

New goods require paid energy inputs (default 0.25 energy units per good).
Primary supply is an exogenous annual domestic resource flow, default 30 units;
it is **not** additional goods capital, inventory, or empirically calibrated
MWh. Energy is not stored. Existing goods inventories can be sold without
using energy again. Healthcare and teaching do not have separately modeled
direct energy requirements, though shortages can ration their goods inputs.

Supply can grow through an exogenous compounded multiplier, default 0% annually.
Growth applies before each year's production, including the first year.
Editing baseline supply preserves that accumulated multiplier; reset starts
it again at one. Generation investment costs, fuels, dispatch, grids, emissions,
imports and renewable/fossil technology mixes are not modeled.

The base quote is €0.20 per energy unit by default, not automatically indexed to
goods inflation. The production-year quote is:

`base price × (1 + scarcity response × clamp(planned demand / available supply
− 0.8, 0, 5))`.

Default scarcity sensitivity is 2. With zero supply and positive demand,
pressure uses its upper bound; a high untraded quote is not a household CPI
observation. No demand means no scarcity premium.

Firms first forecast energy needed for their capital/inventory-based production
plans. Available supply is reserved pro rata, not assigned to the first firm
in the list. Hiring targets are then limited by energy quotas. Working-capital
needs include both payroll and energy; firms must retain enough cash for both
before hiring. Actual energy purchases exactly match actual newly produced
goods × intensity. Unused reservations are curtailed, not resold or reallocated
within the same year. This is a rationing rule, not an efficient spot auction.

Energy costs reduce firm cash profits, business credit affordability and the
cash available for research/dividends. They enter unit-cost pricing alongside
payroll/research, so a shortage can raise input/goods prices even as hiring
falls. It does not guarantee positive aggregate inflation: demand, stocks,
funding and the existing bounded quote adjustment still matter.

Firm payments transfer deposits to a domestic primary-energy provider. It starts
with zero cash, has no bank loan or additional generating-capital asset, and
receives the assumed resource flow without modeled extraction costs or assigned
jobs. Default 80% of its total cash is distributed equally as household resource
income after goods purchases; retained cash carries forward. These payments do
not create deposits and can support demand from the following year. This is a
simplified resource sector, not a calibrated utility business.

Random shocks use a separate seeded energy RNG (5% annual chance when no shock
is active). Default shocks remove 50% of supply for two production years,
including the starting year. They do not randomly stack. A queued scenario
shock pauses playback, starts next year and can refresh/extend an existing
duration. Severity and baseline supply policies apply prospectively, not to
history. Shocks never erase deposits, productive capital or existing goods.

Annual observations reconcile both `available = used + unused` and
`used = new goods output × intensity`. History and firm exports include
physical use, cash bills, quotes, rationing and shock flags; JSON retains up to
1,000 shock events, supply growth and pending/remaining shock state. Planned
output removed by quotas is a diagnostic, **not** measured GDP loss, because
labor or cash might also have constrained production.

## Education, skills and retraining

Education is a fifth discretionary allocation, default 10% of the treasury
budget after mandatory debt service. The provider has a deposit account;
unused cash carries forward. Funding is a transfer, not money creation.
Provider salary/materials payments are **not** additional treasury expenditure
on top of the appropriation.

Opening provider cash funds teachers before goods firms recruit. New
appropriations arrive later, chiefly enabling teaching from the following year.
Candidates have 12 effective basic-study years and are ranked by skill with
seeded tie-breaking. Teachers cannot also work for firms or study full time.
Default annual pay is 0.5 × initial household money, indexed to opening prices.
Teachers are assigned to funded posts; licensing, teacher training and
utility-based career choice are not modeled.

Schooling covers ages 6–17. Eligible ages 18–22 with completed secondary
schooling choose university with default probability 30% when provider cash
exists. Full-time students leave the labor force and cannot borrow against
old employment income for household investment. University needs three
**effective** study years, not automatically three calendar years. Three
successive years below 25% quality cause dropout without a degree bonus.
Completion/dropout changes next year's labor availability, not completed-year
employment statistics.

Unemployed adults can enter training after firm hiring (default annual chance
30%). Teaching capacity for these courses is planned from last year's enrollment.
Training needs two effective years, pauses during employment and can also
complete missing secondary credits. It does not guarantee a job.

Quality is the smaller of teacher coverage and funding coverage, each capped
at one. A teacher supports 15 weighted learners by default; university counts
as 1.5 learners. Actual salaries plus materials are compared with a default
resource target of 0.1 × initial household money per learner, indexed to prices.
With teachers available, 30% of remaining provider cash is offered for materials
after other goods purchases, subject to rationing. Materials are consumed inputs,
not capital. Enrollment without teaching/resources does not generate credits.

Each effective school year adds 0.03 skill points; university completion adds
0.4 and training completion 0.15 by default, up to an index of 3. Adults lose
0.5% of skill annually with a floor of one. Lowering the ceiling blocks new
gains without erasing existing education. Startup cohorts have synthetic prior
basic schooling based on age but skill normalized to one; newborns start at
one without schooling, qualifications or inherited skill bonuses.

Firms rank applicants by skill and pay a default 40% wage premium per point
above one. Worker productivity multiplies firm productivity by
`1 + 0.5 × (skill − 1)` and a technology-familiarity factor. Maximum mismatch
penalty is 20%; schooling improves familiarity gradually and completed
university/retraining updates it to the frontier. Skills can reduce labor
needed for existing orders, so education cannot by itself solve weak demand.

Completed jobs also build skills. Each goods worker or paid teacher adds one
tracked year of experience and gains
`work_skill_gain × max(0, ceiling − skill) / max(ceiling − 1, epsilon)`,
limited by remaining skill room. Default baseline gain is 0.02 points per
working year; learning diminishes near the ceiling. Skill depreciation still
applies, so net skills need not rise every year.

Work also closes 10% of the gap to the technology actually used by the employer
each year (the frontier for teachers). Unused frontier technology does not
automatically become familiar to goods workers. Unemployed residents, retirees
and full-time students gain no work experience. Experience is retained through
job changes/unemployment, starts at zero for the simulated run rather than
invented prior careers, and is not inherited. These are general transferable
skills; occupation-specific experience and part-time hours are not modeled.

Gains arrive **after production**, affecting future years only. Human skills
and qualifications are not priced as financial wealth or productive capital.
Teacher pay is household income. Participation, quality, completions, skills
and attainment use the pre-demographic cohort. Snapshots export tracks,
credits, skills, familiarity and employment sector (employer −1 is education).
Scenario JSON includes retained education events (up to 1,000) and training
capacity plans. These are illustrative conventions, not estimated returns
to education. Private tuition, student debt and a university labor market
are not modeled.

## Business finance, failure and entry

Optional bank working-capital loans require observed sales and **positive past
cash profit**, so unfunded startups cannot borrow on fictional projections.
Total credit is limited to 50% of past sales by default and to stressed profit
affordability, as well as shared bank capital, reserves and money caps.
New terms default to three years at policy rate + loan spread. Existing
contracts keep fixed rates and constant-principal installments.
Interest/principal payments destroy deposits; only collected interest is bank
cash profit. Unpaid business interest is excluded from prudential capital.

Unpaid maturity or consecutive missed payments trigger firm resolution.
Operating losses with less cash than one wage for three consecutive years can
also force exit. Inventories are offered to cash-funded rivals at a liquidation
discount; unbought stock is explicitly scrapped. Remaining cash services loans,
residual claims are written off against bank capital, and any cash surplus goes
to the production holding sector. Leased capital survives. No bailout or debt
transfer to households occurs.

When active firms fall below the startup target, at most one replacement enters
per year if working-age residents can contribute at least one baseline wage.
Default contributions are 2% of worker cash, transferred to the entrant. These
are modeled startup **grants**, not tracked share subscriptions; there is no
household corporate-equity market. Firm distributions are a simplified return
to productive-asset owners. Firms' retained equity remains in their sector.
Entry is not guaranteed when household liquidity is exhausted.

The dashboard/CSV/JSON exposes firm accounts, job assignments, demand forecasts,
adoption, research, cash profits, business loans, entries/failures and active-firm
sales HHI concentration. Firm events retain 1,000 entries. There is no full
industrial sector/input-output model or legal corporate-resolution process.

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

Cash-based **Bank realized profit** equals collected household/business loan interest
plus coupons received on bank-held bonds, less written-off household/business loan
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
accounting identities under varied policy settings. Opening inventories plus output
equals consumption plus investment, education goods, closing inventories, spoilage and scrapping;
closing capital equals
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
