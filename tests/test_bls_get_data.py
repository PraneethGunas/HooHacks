import pytest
from backend.tools.bls_get_data import bls_get_data
from backend.tools.schemas import BlsGetDataOutput


@pytest.mark.asyncio
async def test_bls_total_nonfarm():
    """Fetch total nonfarm employment (national)."""
    result = await bls_get_data(series_ids=["CEU0000000001"], start_year="2023")
    assert isinstance(result, BlsGetDataOutput)
    assert len(result.results) == 1
    series = result.results[0]
    assert series.series_id == "CEU0000000001"
    assert len(series.data) > 0
    print(f"\nTotal nonfarm employment — {len(series.data)} observations:")
    for d in series.data[:3]:
        print(f"  {d.year}-{d.period}: {d.value}")


@pytest.mark.asyncio
async def test_bls_multiple_series():
    """Fetch leisure/hospitality and retail employment together."""
    result = await bls_get_data(
        series_ids=["CEU7000000001", "CEU4142000001"], start_year="2023"
    )
    assert isinstance(result, BlsGetDataOutput)
    assert len(result.results) == 2
    for series in result.results:
        assert len(series.data) > 0
        print(f"\n{series.series_id}: {len(series.data)} observations, latest={series.data[0].value}")
