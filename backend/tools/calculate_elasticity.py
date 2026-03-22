"""
calculate_elasticity — log-log regression for elasticity between two economic variables.

Given two series of (x, y) observations, computes the elasticity (% change in y
per 1% change in x) using OLS on log-transformed values.

Returns: elasticity estimate, 95% CI, R², p-value, and number of observations.

No external stats library needed — pure Python + math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ElasticityResult:
    """Result of an elasticity calculation."""
    elasticity: float          # Point estimate (slope of log-log regression)
    ci_lower: float            # 95% CI lower bound
    ci_upper: float            # 95% CI upper bound
    r_squared: float           # Goodness of fit
    p_value: float             # Statistical significance
    n_observations: int        # Number of data points used
    x_label: str
    y_label: str

    def to_dict(self) -> dict:
        return {
            "elasticity": round(self.elasticity, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "r_squared": round(self.r_squared, 4),
            "p_value": round(self.p_value, 6),
            "n_observations": self.n_observations,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "significant": self.p_value < 0.05,
        }


def _t_distribution_approx(t_stat: float, df: int) -> float:
    """Approximate two-tailed p-value from t-distribution using normal approx."""
    # For df > 30, t-distribution ≈ normal. For smaller df, this is a rough approx.
    # Good enough for a hackathon demo with 10-50 data points.
    z = abs(t_stat)
    # Abramowitz & Stegun approximation for normal CDF
    p = 0.3275911
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    t_val = 1.0 / (1.0 + p * z)
    cdf = 1.0 - (a1 * t_val + a2 * t_val**2 + a3 * t_val**3 + a4 * t_val**4 + a5 * t_val**5) * math.exp(-z * z / 2)
    return 2 * (1 - cdf)  # two-tailed


def _t_critical_approx(df: int, alpha: float = 0.05) -> float:
    """Approximate t-critical value for 95% CI. Rough but sufficient."""
    # For large df, approaches 1.96. For small df, we add a correction.
    if df >= 120:
        return 1.96
    if df >= 30:
        return 2.0
    # Small-sample lookup (common values)
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
             6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
             15: 2.131, 20: 2.086, 25: 2.060}
    if df in table:
        return table[df]
    # Interpolate
    keys = sorted(table.keys())
    for i in range(len(keys) - 1):
        if keys[i] <= df <= keys[i + 1]:
            frac = (df - keys[i]) / (keys[i + 1] - keys[i])
            return table[keys[i]] + frac * (table[keys[i + 1]] - table[keys[i]])
    return 2.0


def calculate_elasticity(
    x_values: list[float],
    y_values: list[float],
    x_label: str = "X",
    y_label: str = "Y",
) -> ElasticityResult:
    """
    Compute elasticity between X and Y using log-log OLS regression.

    Elasticity = d(ln Y) / d(ln X) — the % change in Y for a 1% change in X.

    Args:
        x_values: Independent variable observations (e.g., minimum wage levels)
        y_values: Dependent variable observations (e.g., employment rates)
        x_label: Name for the X variable
        y_label: Name for the Y variable

    Returns:
        ElasticityResult with estimate, CI, R², p-value
    """
    # Filter out non-positive values (can't take log)
    pairs = [(x, y) for x, y in zip(x_values, y_values) if x > 0 and y > 0]
    n = len(pairs)

    if n < 3:
        return ElasticityResult(
            elasticity=0.0, ci_lower=0.0, ci_upper=0.0,
            r_squared=0.0, p_value=1.0, n_observations=n,
            x_label=x_label, y_label=y_label,
        )

    # Log-transform
    ln_x = [math.log(p[0]) for p in pairs]
    ln_y = [math.log(p[1]) for p in pairs]

    # OLS: ln_y = alpha + beta * ln_x  (beta = elasticity)
    mean_x = sum(ln_x) / n
    mean_y = sum(ln_y) / n

    ss_xx = sum((x - mean_x) ** 2 for x in ln_x)
    ss_xy = sum((ln_x[i] - mean_x) * (ln_y[i] - mean_y) for i in range(n))
    ss_yy = sum((y - mean_y) ** 2 for y in ln_y)

    if ss_xx == 0 or ss_yy == 0:
        return ElasticityResult(
            elasticity=0.0, ci_lower=0.0, ci_upper=0.0,
            r_squared=0.0, p_value=1.0, n_observations=n,
            x_label=x_label, y_label=y_label,
        )

    beta = ss_xy / ss_xx  # elasticity estimate
    alpha = mean_y - beta * mean_x

    # Residuals and standard error
    residuals = [ln_y[i] - (alpha + beta * ln_x[i]) for i in range(n)]
    sse = sum(r ** 2 for r in residuals)
    df = n - 2  # degrees of freedom

    r_squared = 1 - (sse / ss_yy) if ss_yy > 0 else 0.0
    r_squared = max(0.0, min(1.0, r_squared))

    if df > 0 and ss_xx > 0:
        se_beta = math.sqrt(sse / df / ss_xx)
        t_stat = beta / se_beta if se_beta > 0 else 0.0
        p_value = _t_distribution_approx(t_stat, df)
        t_crit = _t_critical_approx(df)
        ci_lower = beta - t_crit * se_beta
        ci_upper = beta + t_crit * se_beta
    else:
        p_value = 1.0
        ci_lower = beta
        ci_upper = beta

    return ElasticityResult(
        elasticity=beta,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        r_squared=r_squared,
        p_value=p_value,
        n_observations=n,
        x_label=x_label,
        y_label=y_label,
    )
