import pytest
from backend.tools.fred_get_series import fred_get_series
from backend.tools.schemas import FredSeriesOutput


@pytest.mark.asyncio
async def test_fred_get_series_unrate():
    """Fetch national unemployment rate data."""
    result = await fred_get_series(series_id="UNRATE")
    assert isinstance(result, FredSeriesOutput)
    assert result.series_id == "UNRATE"
    assert result.title
    assert result.units
    assert len(result.recent_observations) > 0
    assert result.latest_value is not None
    print(f"\n{result.title}: latest={result.latest_value} ({result.latest_date})")
    print(f"  {len(result.recent_observations)} observations returned")


@pytest.mark.asyncio
async def test_fred_get_series_fed_min_wage():
    """Fetch federal minimum wage series."""
    result = await fred_get_series(series_id="FEDMINNFRWG")
    assert isinstance(result, FredSeriesOutput)
    assert result.latest_value is not None
    print(f"\nFed min wage: ${result.latest_value}/hr as of {result.latest_date}")
