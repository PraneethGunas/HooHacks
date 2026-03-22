"""Unit tests for code_execute tool — edge cases, safety, complex calculations."""

import pytest
from backend.tools.code_execute import code_execute
from backend.tools.schemas import CodeExecuteOutput


# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_basic_arithmetic():
    r = await code_execute("result = 2 + 2")
    assert r.error is None
    assert r.result == "4"


@pytest.mark.asyncio
async def test_float_precision():
    r = await code_execute("result = round(7.25 * 2.0689655, 2)")
    assert r.error is None
    assert "15" in r.result


@pytest.mark.asyncio
async def test_print_capture():
    r = await code_execute("print('hello world')")
    assert r.error is None
    assert "hello" in r.stdout


@pytest.mark.asyncio
async def test_result_dict():
    code = """
result = {"net": 550.25, "verdict": "better_off"}
"""
    r = await code_execute(code)
    assert r.error is None
    assert "550.25" in r.result
    assert "better_off" in r.result


@pytest.mark.asyncio
async def test_result_list():
    r = await code_execute("result = [1, 2, 3]")
    assert r.error is None
    assert "1" in r.result and "2" in r.result and "3" in r.result


# ---------------------------------------------------------------------------
# Complex economic calculations (what agents actually do)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mortgage_payment():
    code = """
principal = 400000
rate = 0.07 / 12
n = 360
payment = principal * (rate * (1 + rate)**n) / ((1 + rate)**n - 1)
result = round(payment, 2)
"""
    r = await code_execute(code)
    assert r.error is None
    assert float(r.result) == pytest.approx(2661.21, abs=1)


@pytest.mark.asyncio
async def test_rent_elasticity():
    code = """
income_increase_pct = 10.0
elasticity_low = 0.3
elasticity_high = 0.7
median_rent = 1295

rent_increase_low = median_rent * (income_increase_pct / 100) * elasticity_low
rent_increase_high = median_rent * (income_increase_pct / 100) * elasticity_high

result = {
    "rent_increase_low": round(rent_increase_low, 2),
    "rent_increase_high": round(rent_increase_high, 2),
}
"""
    r = await code_execute(code)
    assert r.error is None
    assert "38.85" in r.result  # 1295 * 0.1 * 0.3


@pytest.mark.asyncio
async def test_net_purchasing_power():
    code = """
# Income side
wage_increase = 520  # $5/hr * 104 hrs/month
tax_rate = 0.22
net_wage = wage_increase * (1 - tax_rate)

# Cost side
grocery_increase = 6.75
restaurant_increase = 10
childcare_increase = 24
retail_increase = 3
rent_increase = 24
other_increase = 3
total_cost = grocery_increase + restaurant_increase + childcare_increase + retail_increase + rent_increase + other_increase

net = net_wage - total_cost
result = {"net_wage": round(net_wage, 2), "total_cost": round(total_cost, 2), "net": round(net, 2)}
"""
    r = await code_execute(code)
    assert r.error is None
    assert "net" in r.result


@pytest.mark.asyncio
async def test_budget_share_weighted_impact():
    code = """
monthly_income = 2917  # $35K/year / 12
budget_shares = {"groceries": 0.11, "restaurants": 0.04, "transport": 0.16, "healthcare": 0.08}
price_changes = {"groceries": 0.015, "restaurants": 0.04, "transport": 0.005, "healthcare": 0.01}

costs = {}
for cat in budget_shares:
    costs[cat] = round(monthly_income * budget_shares[cat] * price_changes[cat], 2)

total = round(sum(costs.values()), 2)
result = {"costs": costs, "total_monthly_cost_increase": total}
"""
    r = await code_execute(code)
    assert r.error is None
    assert "total_monthly_cost_increase" in r.result


# ---------------------------------------------------------------------------
# Safety / Sandbox
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_blocked_import():
    r = await code_execute("import os")
    assert r.error is not None
    assert "Blocked" in r.error


@pytest.mark.asyncio
async def test_blocked_open():
    r = await code_execute("open('/etc/passwd')")
    assert r.error is not None
    assert "Blocked" in r.error


@pytest.mark.asyncio
async def test_blocked_exec():
    r = await code_execute("exec('print(1)')")
    assert r.error is not None
    assert "Blocked" in r.error


@pytest.mark.asyncio
async def test_blocked_dunder():
    r = await code_execute("x = ''.__class__.__bases__")
    assert r.error is not None
    assert "Blocked" in r.error


@pytest.mark.asyncio
async def test_blocked_subprocess():
    r = await code_execute("subprocess.run(['ls'])")
    assert r.error is not None
    assert "Blocked" in r.error


@pytest.mark.asyncio
async def test_runtime_error_caught():
    r = await code_execute("result = 1 / 0")
    assert r.error is not None
    assert "ZeroDivisionError" in r.error


@pytest.mark.asyncio
async def test_name_error_caught():
    r = await code_execute("result = undefined_variable")
    assert r.error is not None
    assert "NameError" in r.error


# ---------------------------------------------------------------------------
# Allowed modules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_math_module():
    r = await code_execute("result = math.sqrt(144)")
    assert r.error is None
    assert "12" in r.result


@pytest.mark.asyncio
async def test_statistics_module():
    r = await code_execute("result = statistics.mean([10, 20, 30, 40])")
    assert r.error is None
    assert "25" in r.result


@pytest.mark.asyncio
async def test_decimal_module():
    r = await code_execute("result = str(Decimal('7.25') * Decimal('2.07'))")
    assert r.error is None
    assert "15.0075" in r.result


@pytest.mark.asyncio
async def test_json_in_sandbox():
    r = await code_execute('result = json.dumps({"a": 1})')
    assert r.error is None
    assert '"a"' in r.result
