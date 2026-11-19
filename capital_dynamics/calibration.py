"""Dated official reference observations, not fitted simulation parameters.

No network requests occur during simulation or tests. See docs/calibration.md
for definitions, reference-period differences and the remaining calibration work.
"""
RETRIEVED_ON = "2026-11-19"
RELATIVE_LOW_INCOME_FRACTION = 0.6

REFERENCE_BENCHMARKS = (
    {
        "Indicator": "Median equivalised disposable income",
        "Observation": "€22,939 / year",
        "Area": "EU27",
        "Period": "EU-SILC 2025 (income reference 2024)",
        "Source": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_di03?geo=EU27_2020&time=2025&age=TOTAL&sex=T&statinfo=MED_EI&unit=EUR",
        "Use": "Calibration target only: household-equivalised income is not personal income or a starting deposit.",
    },
    {
        "Indicator": "Relative poverty threshold",
        "Observation": "60% of national median equivalised disposable income",
        "Area": "EU-SILC methodology",
        "Period": "Current definition",
        "Source": "https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Living_conditions_in_Europe_-_income_distribution_and_income_inequality",
        "Use": "60% convention used for a personal-income proxy; no claim of Eurostat-equivalent household poverty.",
    },
    {
        "Indicator": "Aggregate pension replacement ratio",
        "Observation": "0.60 (60%)",
        "Area": "EU27, total sex",
        "Period": "EU-SILC 2025",
        "Source": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ilc_pnp3?geo=EU27_2020&time=2025&sex=T",
        "Use": "Reference: median gross pensions ages 65–74 / median gross earnings ages 50–59, not an individual's replacement rate.",
    },
    {
        "Indicator": "New loans to sole proprietors / unincorporated partnerships",
        "Observation": "4.36% annual agreed rate",
        "Area": "Euro area",
        "Period": "September 2026; published 2 November 2026",
        "Source": "https://www.ecb.europa.eu/press/stats/mfi/html/ecb.mir2611~2502265512.en.html",
        "Use": "Indicative investment-credit rate benchmark; variable/fixation up to one year is not this model's fixed ten-year contract.",
    },
    {
        "Indicator": "Household assets, debt, income and consumption distributions",
        "Observation": "HFCS 2023 wave; October 2026 tables",
        "Area": "Euro-area households; national reference dates differ",
        "Period": "Mainly 2023; country surveys 2022–2025",
        "Source": "https://www.ecb.europa.eu/home/pdf/research/hfcn/HFCS_Statistical_Tables_Wave_2023_October_2026.pdf",
        "Use": "Source for joint initialization and credit-risk validation. Household conditional medians must not become per-person deposits.",
    },
)
