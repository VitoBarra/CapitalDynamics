# Monetary economy: accounting and assumptions

The app opens directly into this experimental monetary model. The legacy
dashboard is retired; legacy wealth balances are not automatically converted.
Existing monetary sessions retain their state. Load a comparison preset or
create a fresh scenario to explore alternatives.

## Starting accounts

Defaults: 100 residents, 1 money unit each, 200 real productive-capital units,
100 producer money units and 20 bank-capital units. Capital initially belongs
equally to residents. The price level starts at 1. Initial deposits total 200;
bank reserves are 220, so bank equity is 20. The fiat issuer has a matching
220 reserve liability and negative equity. This explicitly offsets initial
financial endowments: consolidated sector net worth equals real capital at
current prices. These are illustrative settings, not estimates.

Each resident has deposits, real productive capital, bonds and loan obligations.
Net wealth = deposits + capital × price + bonds at face value − loan principal
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
4. Issue any permitted fiat grant; sell new government bonds, subject to
   buyer willingness, bank constraints and the debt ceiling. Bond proceeds
   and grants are financing, not taxes.
5. Freeze one common total treasury budget. Reserve each policy's percentage
   of this total, including debt service. Pay UBI, budget-limited pensions,
   healthcare and existing bond obligations from their own envelopes.
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
25%, investment 15%, debt service 5%, unallocated 10%.

The denominator is **all treasury money available at allocation time**:
opening money + collected taxes + bond proceeds + fiat grants. Debt service
does not silently change that denominator. Changing display/section order
does not change allocations. Unused pension, investment or debt allocations
stay in treasury; they do not spill into another policy.

The allocation bar always includes unallocated funds. A second bar shows
**actual cash expenditure percentages**, with a different denominator: the
sum actually paid. Tables show allocated, spent and unused amounts. Bond
principal repayment is a cash outflow here, not an operating expense.
Charts describe the last recorded year; policy changes apply next year.

## Bonds and government shortfalls

Adults offer a configurable fraction of deposits for new bonds. Their
purchases transfer existing money. The bank can purchase a separate fraction
of the borrowing target, creating a treasury deposit against a bond asset.
Both buyer groups purchase at face value. There is no secondary bond market
or endogenous risk premium. The ceiling limits new issuance, not outstanding
contracts retroactively. Lowering the ceiling below existing debt freezes new
issuance until debt falls; it does not cancel debt.

Contracts retain their issue-time coupon and maturity. Within the fixed debt
envelope, choose coupon-first or principal-first. Each category is paid pro
rata across bondholders. Unpaid coupons are cancelled and reported as debt
service shortfall (no accumulating sovereign coupon arrears). At maturity,
unfunded principal is written off and reported explicitly. Bank-held losses
reduce bank equity. New borrowing can support refinancing, but cannot
temporarily exceed the debt ceiling.

## Banking

Investment loans are limited by a resident's productive assets and bond
collateral value, existing debt, loan demand, bank capital and reserve ratios.
Loans and bank-held government bonds have 100% risk weight. Loans create
equal deposits and liabilities: borrowing alone does not create net wealth.
Principal repayment destroys deposits and reduces the bank loan asset.
Interest payments reduce deposits and become bank equity; distributions
recreate deposits against equity. Unpaid interest accrues as a bank asset and
borrower liability. Contracts keep their original fixed rate (policy rate +
spread), installments and maturity. Consecutive missed-payment limits or
unpaid maturity balances trigger default; the bank bears the remaining loss.

An insolvent bank stops extending credit. Deposits remain recorded claims:
there is **no bailout, resolution scheme, deposit insurance or bank-run
simulation**. There are no consumption loans, competing banks or adjustable
loan rates. These are intentional first-version boundaries.

On death, liquid estate money and producer-funded sales of capital/bonds
settle debts before inheritance. Sales depend on producer liquidity; unsold
assets can pass to heirs/the state, while unrecovered debt is written off.
Only surviving children inherit. Government acquisition of its own bonds
cancels those bonds rather than creating cash revenue.

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

New monetary scenarios default to **0% minimum and 60% maximum net wealth
tax**, with progressivity 2. Existing scenarios, including their original tax
rates and recorded history, are retained. Loading a comparison preset creates
a fresh scenario using the new defaults.

The sidebar's **Display** tab controls percentile groups, individual wealth
visibility/log scale, and age bins/units. Individual wealth and percentile
shares reuse the legacy viridis colors. Negative net wealth is shown as signed
percentile totals, never clipped into a pie. The dashboard includes net wealth
Gini history, the active tax curve, actual applied tax rates, healthcare patient
choices and mortality trends. New observations start on the next year for
existing sessions; unavailable historical readings remain gaps rather than
invented zeros. Population, percentile, contract and account data remain
available in detailed tables and downloads. The annual finance ledger records
opening treasury money, taxes, borrowing, issuance, estates, policy/debt-service
payments, closing money and reconciliation error, with a separate CSV download.

Production reporting also tracks failed private investments, capital added and
capital shortfall relative to full investment efficiency. A failure counts only
when goods were actually purchased. Shortfall is forgone new capital, not lost
money or destruction of existing household assets. Real household net wealth
and productive capacity share a trend chart, but capacity is not a wealth cap:
there is no dashed ceiling or legacy logistic wealth-growth/random-loss process.

Tests check matching assets/liabilities, money creation/destruction, sector
consolidation, government reconciliation, defaults, estate settlement, caps,
resumption, UI controls and live fragment refreshes. Downloads include sector
balances, household accounts, contracts, retained history and a bounded
transaction ledger. Settings are a reproducibility description, not a full
state checkpoint. History retains 10,000 years, transactions 10,000 entries,
and policy history 1,000 interventions.
