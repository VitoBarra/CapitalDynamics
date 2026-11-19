"""One denominator and one validation rule for public policy allocations."""
import math

POLICIES = ("UBI", "Pensions", "Healthcare", "Public investment", "Debt service")
COLORS = ["#4477AA", "#EE9933", "#228866", "#AA66AA", "#CC5555", "#999999"]
ALLOCATION_FIELDS = ("ubi_budget_fraction", "pension_budget_fraction",
                     "healthcare_spending_fraction", "investment_budget_fraction", "debt_service_fraction")


def validate_allocations(shares):
    if len(shares) != len(POLICIES) or any(not math.isfinite(x) or not 0 <= x <= 1 for x in shares):
        raise ValueError("Each allocation must be between 0% and 100%.")
    if sum(shares) > 1 + 1e-10:
        raise ValueError(f"Allocations total {sum(shares):.1%}. Reduce them to 100% or less.")


def allocate(total, shares):
    validate_allocations(shares)
    return dict(zip(POLICIES, (max(total, 0) * share for share in shares)))


def allocation_rows(total, shares, spent):
    """Budget shares and expenditure shares are intentionally different columns."""
    amounts = allocate(total, shares)
    expenditure = sum(spent.values())
    rows = [{"Policy": name, "Allocation (% of total budget)": share * 100,
             "Allocated": amounts[name], "Spent": spent.get(name, 0),
             "Unused": max(0, amounts[name] - spent.get(name, 0)),
             "Actual (% of expenditure)": spent.get(name, 0) / expenditure * 100 if expenditure else 0}
            for name, share in zip(amounts, shares)]
    retained = max(0, 1 - sum(shares))
    rows.append({"Policy": "Unallocated", "Allocation (% of total budget)": retained * 100,
                 "Allocated": total * retained, "Spent": 0, "Unused": total * retained,
                 "Actual (% of expenditure)": 0})
    return rows
