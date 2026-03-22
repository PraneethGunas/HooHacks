"""
run_scenario_analysis — project base/bull/bear scenarios given a policy shock.

Takes a baseline value, applies a shock (% change), and uses an elasticity
estimate with uncertainty to produce three scenarios: base case, bull case
(optimistic), and bear case (pessimistic).

This is the data science computation tool that gives PolicyPulse its
quantitative edge — agents don't just say "wages will rise", they produce
"base: +6.2%, bull: +8.1%, bear: +3.4%" with stated assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScenarioResult:
    """Three-scenario projection from a policy shock."""
    variable_name: str
    baseline_value: float
    shock_pct: float             # The policy shock as % change
    elasticity: float            # Estimated elasticity used

    # Base case: use point estimate of elasticity
    base_projected: float
    base_pct_change: float

    # Bull case: optimistic (higher elasticity if positive shock, lower if negative)
    bull_projected: float
    bull_pct_change: float

    # Bear case: pessimistic (opposite of bull)
    bear_projected: float
    bear_pct_change: float

    assumptions: list[str]

    def to_dict(self) -> dict:
        return {
            "variable_name": self.variable_name,
            "baseline_value": round(self.baseline_value, 2),
            "shock_pct": round(self.shock_pct, 2),
            "elasticity": round(self.elasticity, 4),
            "scenarios": {
                "base": {
                    "projected_value": round(self.base_projected, 2),
                    "pct_change": round(self.base_pct_change, 2),
                },
                "bull": {
                    "projected_value": round(self.bull_projected, 2),
                    "pct_change": round(self.bull_pct_change, 2),
                },
                "bear": {
                    "projected_value": round(self.bear_projected, 2),
                    "pct_change": round(self.bear_pct_change, 2),
                },
            },
            "assumptions": self.assumptions,
        }


def run_scenario_analysis(
    variable_name: str,
    baseline_value: float,
    shock_pct: float,
    elasticity: float,
    elasticity_ci_lower: float | None = None,
    elasticity_ci_upper: float | None = None,
    uncertainty_pct: float = 30.0,
    assumptions: list[str] | None = None,
) -> ScenarioResult:
    """
    Project base/bull/bear scenarios for a variable under a policy shock.

    The shock propagates through the elasticity:
        % change in Y = elasticity * shock_pct

    Args:
        variable_name: What we're projecting (e.g., "median hourly wage")
        baseline_value: Current value of the variable
        shock_pct: The policy shock as % change (e.g., 40.0 for a 40% min wage increase)
        elasticity: Point estimate of the elasticity
        elasticity_ci_lower: Lower bound of elasticity CI (optional)
        elasticity_ci_upper: Upper bound of elasticity CI (optional)
        uncertainty_pct: If no CI provided, use this % above/below elasticity for scenarios
        assumptions: List of assumptions underlying this projection

    Returns:
        ScenarioResult with base/bull/bear projections
    """
    if assumptions is None:
        assumptions = [
            f"Baseline value: {baseline_value}",
            f"Policy shock: {shock_pct}%",
            f"Elasticity estimate: {elasticity}",
            "Linear approximation (valid for small shocks)",
            "Ceteris paribus — no other policy changes",
        ]

    # Base case: point estimate
    base_pct = elasticity * shock_pct
    base_projected = baseline_value * (1 + base_pct / 100)

    # Bull and bear: use CI if available, otherwise apply uncertainty band
    if elasticity_ci_lower is not None and elasticity_ci_upper is not None:
        e_optimistic = elasticity_ci_upper
        e_pessimistic = elasticity_ci_lower
    else:
        band = abs(elasticity) * (uncertainty_pct / 100)
        e_optimistic = elasticity + band
        e_pessimistic = elasticity - band

    # "Bull" = better outcome for the affected variable
    # If shock is positive and elasticity is positive, higher elasticity = more growth = bull
    # If shock is negative, higher elasticity = more decline = bear
    if shock_pct >= 0:
        bull_elasticity = e_optimistic
        bear_elasticity = e_pessimistic
    else:
        bull_elasticity = e_pessimistic  # Less decline
        bear_elasticity = e_optimistic   # More decline

    bull_pct = bull_elasticity * shock_pct
    bull_projected = baseline_value * (1 + bull_pct / 100)

    bear_pct = bear_elasticity * shock_pct
    bear_projected = baseline_value * (1 + bear_pct / 100)

    return ScenarioResult(
        variable_name=variable_name,
        baseline_value=baseline_value,
        shock_pct=shock_pct,
        elasticity=elasticity,
        base_projected=base_projected,
        base_pct_change=base_pct,
        bull_projected=bull_projected,
        bull_pct_change=bull_pct,
        bear_projected=bear_projected,
        bear_pct_change=bear_pct,
        assumptions=assumptions,
    )
