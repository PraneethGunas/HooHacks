from __future__ import annotations

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import BEADataPoint, BEARegionalOutput

BEA_API_URL = "https://apps.bea.gov/api/data/"


async def bea_regional_data(
    table_name: str,
    geo_fips: str,
    year: str = "2023",
    line_code: str = "1",
) -> BEARegionalOutput:
    """Fetch regional economic data from the Bureau of Economic Analysis.

    Args:
        table_name: BEA table, e.g. "SARPP" (state price parities),
                    "MARPP" (metro), "CAINC1" (personal income).
        geo_fips: Geography FIPS, e.g. "51000" for Virginia.
        year: Year or "LAST5" for latest 5 years.
        line_code: Line code within the table (varies by table).
    """
    if not settings.bea_data_api:
        return BEARegionalOutput(
            table_name=table_name,
            geo_fips=geo_fips,
            data=[BEADataPoint(value="ERROR: BEA_DATA_API key not configured. Set it in .env.")],
        )

    params = {
        "UserID": settings.bea_data_api,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": table_name,
        "GeoFIPS": geo_fips,
        "Year": year,
        "LineCode": line_code,
        "ResultFormat": "JSON",
    }

    raw = await fetch_json(BEA_API_URL, params=params)

    # BEA wraps results in BEAAPI.Results
    results = raw.get("BEAAPI", {}).get("Results", {})

    # Check for error
    if "Error" in results:
        error_msg = results["Error"].get("ErrorDetail", {}).get("Description", "Unknown error")
        return BEARegionalOutput(
            table_name=table_name,
            geo_fips=geo_fips,
            data=[BEADataPoint(value=f"ERROR: {error_msg}")],
        )

    data_rows = results.get("Data", [])
    points = [
        BEADataPoint(
            year=row.get("TimePeriod", ""),
            value=row.get("DataValue", ""),
            geo_name=row.get("GeoName", ""),
            unit=row.get("UNIT_MULT", ""),
        )
        for row in data_rows
    ]

    return BEARegionalOutput(
        table_name=table_name,
        geo_fips=geo_fips,
        data=points,
    )
