# Capital Dynamics

An interactive euro-denominated monetary economy sandbox with production, prices, banking, government bonds, taxes, UBI, pensions, healthcare and demographics. It is an experimental accounting model, not a forecast or a calibrated model of the euro area.

## Getting started

### Windows with Docker

Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Linux containers enabled. From PowerShell in the project folder:

```powershell
docker build -t capital-dynamics .
docker run --rm -p 8501:8501 capital-dynamics
```

Open http://localhost:8501 in your browser. Stop the container with `Ctrl+C`. If port 8501 is already in use, replace `-p 8501:8501` with `-p 8502:8501` and open http://localhost:8502 instead. Rebuild the image after changing application code.

### Local Python

Requires Python 3.10+ and internet access to install dependencies. On Windows, from PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

Run tests with `.\.venv\Scripts\python -m unittest discover -s tests -v`.

### Docker with Make

If `make` is installed, it can build and run the Docker image:

```bash
make run
```

Open http://localhost:8501; stop with `Ctrl+C`. `make build` builds the image, `make test` runs the regression suite in a container, and `make help` lists commands. The tests are mounted read-only from the project folder.

Optionally create a Git-ignored `.env.local` using Makefile assignments without shell quotes:

```makefile
PORT=8502
IMAGE=capital-dynamics
```

Available settings: `PORT` (host port, default 8501) and `IMAGE` (default `capital-dynamics`). Command-line overrides take priority, e.g. `make run PORT=8503`.

## Run a scenario

The app contains one monetary model. There are no old-model adapters, session migrations or alternate budget regimes. Restart the Streamlit app after updating; old running sessions and scripts using removed APIs are not supported.

- **Scenario:** choose one of six reproducible comparison presets, or create an economy using a seed, population, household money, productive capacity, producer money and bank capital.
- **Batch:** advance a chosen number of years in the same economy.
- **Live:** start, pause, resume or single-step while paused. Refresh interval and years per refresh control playback speed. Live playback stops on extinction.
- **Reset monetary scenario:** restart using the active policies and original seed. A cap below initial money supply is rejected without discarding the current economy.
- **Display:** adjust trend window, percentile groups, individual visibility/log scale, age bins and share/count units without resetting the economy.

Open section-local settings and select **Apply policy**. Changes affect the next year without resetting population, contracts, history or the random sequence. Existing loan and bond terms remain unchanged. Policy forms stay outside timed chart refreshes so live updates do not interrupt draft inputs.

## Dashboard and reporting

Major sections have bordered boxes. The app supports coordinated light and dark appearances through Streamlit settings.

| Section | Charts and collected data |
| --- | --- |
| Current wealth distribution | Individual net wealth, percentile shares, nominal/real wealth and Gini history. Negative wealth uses signed percentile totals rather than a misleading pie; conventional Gini is unavailable when any household has negative wealth. |
| Living standards and income | Median personal disposable income and purchasing power, personal low-income proxy, consumption per resident, age-band pension replacement ratio, and dated official calibration references. |
| Economy and production | Productive capacity, output, consumption, investment, real household net wealth versus capacity, private capital added, failed investments and capital shortfalls. |
| Government budget and taxes | Tax curve, actual applied rates, tax receipts, treasury money/debt, funding sources, common-budget allocation, latest spending breakdown, expenditure history and annual cash reconciliation. |
| UBI and pensions | Equal UBI, pension payments, recipient/eligibility data and pension shortfalls. |
| Healthcare, aging and mortality | Public funding, private premiums, provider money, public/private patient counts, mortality history and death-risk curves by age. |
| Banking and credit | Income-stressed affordability, borrower risk premiums, collateral recovery, residual losses, book/prudential equity, unpaid interest and cash-based bank profit. |
| Money and prices | Base/broad money, inflation and price level. |
| Population age distribution | Age bins and population/death history. |

Productive capacity is real capital, not a ceiling on household wealth. Investment failures reduce newly created capital, not bank deposits or existing wealth. Goods and capital have physical model units, separate from euros.

### Euro amounts and units

Deposits, taxes, payments, debt, bank reserves and nominal wealth are expressed in **euros (€ / EUR)**. Real wealth is expressed in **year-0 euros**. Monetary inputs, metrics, chart axes/tooltips and table columns identify their currency. CSV headers carry units while amounts stay numeric; scenario JSON declares `"currency": "EUR"`.

Starting values remain deliberately small illustrative amounts (for example, €1 per resident), not estimates of European household finances. Calculations retain full precision, including fractions of a cent; display rounding does not change account balances. The price index starts at 1, corresponding to €1 per goods/capital unit at year zero.

### Mortality reporting

All expected mortality series average age-specific risks over the **same cohort before deaths, aging and births**. Unfunded mortality assumes nobody receives protection; public-care mortality assumes everybody receives current public care; expected mortality uses actual public/private care choices. Observed mortality is actual deaths divided by that cohort's size. Year zero has modeled risks but no observed death interval.

### Credit risk and living standards

Loans need observed repayment income as well as collateral. Underwriting applies configurable income/rate stresses and counts existing debt service. A transparent score adds a borrower-specific premium; arrears and a post-default exclusion period block fresh loans. Defaults and estates attempt discounted collateral sales, limited by producer liquidity, before writing off residual debt. Unpaid household interest remains in book accounts but cannot fund lending or bank distributions.

Annual personal disposable income includes cash wages, transfers, household dividends and bond coupons, less wealth tax and loan interest actually paid. Loans, sales, inheritance and capital gains are not income; principal repayments are not income deductions. Annual living-standard measures use the same cohort before deaths and births. The low-income measure is a **personal-income proxy**, not household-equivalised Eurostat poverty; a non-positive median leaves it undefined. The pension ratio compares age bands, not each individual's previous salary.

### Official data research

[Calibration sources and implementation plan](docs/calibration.md) records verified Eurostat income/pension observations, the 60% poverty convention, ECB lending-rate/HFCS data, EBA creditworthiness principles, and demographic/healthcare datasets. References carry periods, definitions and retrieval dates, and are available in the dashboard without network requests. These are **not automatically fitted defaults**: household income is not a starting deposit, and household statistics cannot simply be assigned to individual residents.

### Shared-budget allocation

Set all percentages together under **Government budget and taxes → Budget allocation settings**. UBI, pensions, healthcare, public investment and debt service each use the same total treasury budget. Totals above 100% are rejected atomically. Unallocated or unused funds stay with government; unused pension allocations do not increase another policy's allocation.

Allocation and actual-expenditure bars have explicit, separate denominators and matching policy colors. Figures describe the last recorded year; active policy changes apply next year.

### Data and downloads

Under **Accounts, contracts and downloads**, inspect and download:

- Resident snapshots: IDs, age, parent links, deposits, real assets, bonds, debt, nominal/real net wealth, wages, UBI, pensions, personal income, taxes/interest paid, consumption, repayment income, risk/default history, healthcare preference/choice, premiums and death probability.
- Retained annual history, including year zero and all recorded aggregate observations.
- Annual government finance ledger: opening money, taxes, borrowing, issuance, estates, payments, closing money and reconciliation error.
- Sector balance sheets and transaction ledger, including labeled non-cash events.
- Loan/bond contracts, percentile shares, policy changes, and scenario settings (seed, initial/current parameters, contracts and interventions).

History retains 10,000 years; the transaction ledger retains 10,000 entries and policy history 1,000 changes. Downloads include retained records, not unlimited archives. Settings document the run, not a full state checkpoint; reproducing a long run also requires any policy changes that have aged out of the retained history.

## Assumptions and limitations

See [Monetary model accounting and assumptions](docs/monetary-model.md) for defaults, annual sequence, money definitions, accounting identities, demographic rules and limitations. Base money is bank reserves; broad money includes all non-bank deposits, including the treasury, producers and healthcare providers. Printing money does not directly create productive capacity.

Healthcare effects and economic rates are illustrative. Mortality is stochastic with infant, young-adult and exponentially increasing adult hazards, with no maximum-age cutoff. There is no automatic indefinite improvement in mortality. Reference context: [SSA 2022 life table](https://www.ssa.gov/oact/STATS/table4c6_2022_TR2025.html) and [Our World in Data mortality by age](https://ourworldindata.org/how-do-the-risks-of-death-change-as-people-age).

Tests verify accounting identities, goods use and capital accumulation across varied policies, currency-scale-independent taxation, consistent bond collateral in lending, and comparable mortality reporting. These establish internal consistency for tested scenarios, **not empirical validity**. Inflation, consumption, credit demand and healthcare quality are not fitted to real data; healthcare has no staffing/capacity market.

## Project files

- `app.py`: Single monetary-dashboard entrypoint.
- `capital_dynamics/monetary.py` / `monetary_ui.py`: Monetary accounting, policies, playback, charts and downloads.
- `capital_dynamics/budget.py` / `budget_ui.py`: Allocation validation and visualizations.
- `capital_dynamics/ui_components.py` / `dashboard_charts.py`: Native controls and reusable charts.
- `capital_dynamics/economics.py`: Taxation, inequality, fertility and age-specific mortality calculations.
- `capital_dynamics/currency.py`: Euro presentation and numeric export units.
- `capital_dynamics/help_text.py`: Plain-language explanations for controls, charts and tables.
- `capital_dynamics/calibration.py`: Offline, dated official reference observations and definitions.
- `Dockerfile`: Linux container for running the dashboard with Docker Desktop.
- `tests/`: Model, accounting and interface regression checks.
