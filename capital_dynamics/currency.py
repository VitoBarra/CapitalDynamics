"""Euro presentation and export units; calculations retain full precision."""
import math


MONEY_COLUMNS = {
    "Money", "Net wealth", "Government money", "Government debt", "Bank equity",
    "Outstanding loans", "Bonds", "Debt", "UBI", "Pension", "Wages", "Private premium",
    "Healthcare sector money", "Policy budget", "Tax revenue", "Unpaid wealth tax",
    "Borrowing proceeds", "Money issued", "Estate revenue", "Estate debt cancellation",
    "Pension shortfall", "Private premiums", "Base money", "Broad money", "UBI per person",
    "Loans originated", "Loan interest accrued", "Loan interest paid", "Loan principal repaid",
    "Loan defaults", "Bank bond credit", "Bank bond repayments", "Bank distributions",
    "Bond interest paid", "Bond principal repaid",
    "Debt service due", "Debt service shortfall", "Consumption", "Opening government money",
    "Total government spending", "Money balance error", "Base money balance error",
    "Government balance error", "Assets", "Liabilities", "Net worth", "Error", "Amount",
    "Allocated", "Spent", "Unused", "principal", "installment", "arrears",
    "Taxable wealth",
    "Median disposable income", "Low-income threshold", "Consumption per person",
    "Disposable income", "Income received", "Wealth tax paid", "Verified repayment income",
    "Loan recoveries", "Loan principal losses", "Bank bond interest received", "Bank bond principal losses",
    "Bank realized profit", "Prudential bank equity", "Unpaid loan interest",
    "Government market debt", "Government arrears", "Opening government debt", "Bond interest accrued",
    "Refinanced principal", "Sovereign debt written off", "Sovereign market losses", "Government debt balance error",
    "Bank bond valuation change", "Bond face value", "Bond interest arrears", "Market value",
    "Principal cancelled", "Interest cancelled", "Creditor market loss", "Bank principal loss",
    "Desired goods spending", "Output at trade prices",
}
for _policy in ("UBI", "Pensions", "Healthcare", "Public investment", "Debt service"):
    MONEY_COLUMNS.update((f"{_policy} spent", f"{_policy} allocated"))

REAL_MONEY_COLUMNS = {"Real net wealth", "Median real disposable income"}
CAPITAL_COLUMNS = {"Productive capacity", "Real productive assets", "Private capital added", "Private capital shortfall"}
GOODS_COLUMNS = {"Output", "Real consumption", "Real investment", "Real consumption per person", "Unsold goods"}


def euro(value, decimals=2):
    return "Not recorded" if value is None or not math.isfinite(value) else f"€{value:,.{decimals}f}"


def column_unit(name):
    if name in MONEY_COLUMNS:
        return "EUR"
    if name in REAL_MONEY_COLUMNS:
        return "EUR, year-0 prices"
    if name in CAPITAL_COLUMNS:
        return "capital units"
    if name == "Real consumption per person":
        return "goods/person/year"
    if name in GOODS_COLUMNS:
        return "goods/year"
    return ""


def export_frame(frame):
    """Keep CSV amounts numeric and carry currency/real-unit metadata in headers."""
    return frame.rename(columns={
        name: f"{name} ({column_unit(name)})" for name in frame.columns if column_unit(name)
    })
