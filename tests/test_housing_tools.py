import pytest
from backend.tools.census_acs_query import census_acs_query
from backend.tools.bea_regional_data import bea_regional_data
from backend.tools.hud_data import hud_data
from backend.tools.code_execute import code_execute
from backend.tools.schemas import (
    CensusACSOutput,
    BEARegionalOutput,
    HUDDataOutput,
    CodeExecuteOutput,
)


# --- Census ACS ---

@pytest.mark.asyncio
async def test_census_median_rent_virginia():
    """Fetch median gross rent for Virginia counties."""
    result = await census_acs_query(
        table_variables=["B25064_001E"],
        geography="county:*",
        state_fips="51",
        year=2023,
    )
    assert isinstance(result, CensusACSOutput)
    assert len(result.rows) > 0
    assert "B25064_001E" in result.headers
    print(f"\nCensus ACS: {len(result.rows)} Virginia counties, headers={result.headers}")
    for row in result.rows[:3]:
        print(f"  {row}")


@pytest.mark.asyncio
async def test_census_median_home_value():
    """Fetch median home value for Fairfax County, VA."""
    result = await census_acs_query(
        table_variables=["B25077_001E", "B19013_001E"],
        geography="county:059",
        state_fips="51",
    )
    assert isinstance(result, CensusACSOutput)
    assert len(result.rows) >= 1
    print(f"\nFairfax County: {result.rows[0]}")


# --- BEA Regional ---

@pytest.mark.asyncio
async def test_bea_state_price_parities():
    """Fetch state-level regional price parities for Virginia."""
    result = await bea_regional_data(
        table_name="SARPP",
        geo_fips="51000",
        year="2023",
        line_code="1",
    )
    assert isinstance(result, BEARegionalOutput)
    assert len(result.data) > 0
    print(f"\nBEA SARPP Virginia: {len(result.data)} data points")
    for d in result.data[:3]:
        print(f"  {d.year}: {d.value} ({d.geo_name})")


# --- HUD ---

@pytest.mark.asyncio
async def test_hud_fmr_virginia():
    """Fetch Fair Market Rents for Virginia."""
    result = await hud_data(dataset="fmr", entity_id="VA")
    assert isinstance(result, HUDDataOutput)
    assert result.data
    data = result.data if isinstance(result.data, dict) else {}
    print(f"\nHUD FMR Virginia: {type(result.data).__name__}, keys={list(data.keys())[:5] if isinstance(data, dict) else 'list'}")


# --- Code Execute ---

@pytest.mark.asyncio
async def test_code_execute_basic_math():
    """Test basic arithmetic."""
    result = await code_execute("result = 7.25 * 2.07")
    assert isinstance(result, CodeExecuteOutput)
    assert result.error is None
    assert result.result is not None
    print(f"\n7.25 * 2.07 = {result.result}")


@pytest.mark.asyncio
async def test_code_execute_mortgage_calc():
    """Test mortgage payment calculation."""
    code = """
# Monthly mortgage payment calculation
principal = 400000
annual_rate = 0.07
monthly_rate = annual_rate / 12
n_payments = 30 * 12
payment = principal * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
result = f"${payment:,.2f}/month"
"""
    result = await code_execute(code)
    assert result.error is None
    assert "$" in result.result
    print(f"\nMortgage payment on $400K at 7%: {result.result}")


@pytest.mark.asyncio
async def test_code_execute_blocked_import():
    """Verify that import statements are blocked."""
    result = await code_execute("import os\nos.listdir('/')")
    assert result.error is not None
    assert "Blocked" in result.error
    print(f"\nBlocked import: {result.error}")


@pytest.mark.asyncio
async def test_code_execute_affordability():
    """Test rent-to-income ratio calculation."""
    code = """
monthly_rent = 1800
annual_income = 55000
monthly_income = annual_income / 12
rent_to_income = (monthly_rent / monthly_income) * 100
burden = "cost-burdened" if rent_to_income > 30 else "affordable"
result = {
    "rent_to_income_pct": round(rent_to_income, 1),
    "status": burden,
    "monthly_income": round(monthly_income, 2),
}
"""
    result = await code_execute(code)
    assert result.error is None
    assert "rent_to_income_pct" in result.result
    print(f"\nAffordability calc: {result.result}")
