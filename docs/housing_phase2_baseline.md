# Housing Phase 2: Housing Market Baseline

```json
{
  "supply_metrics": [
    {
      "metric_name": "Housing Starts: Total Units",
      "value": "1,487,000 units (annualized)",
      "source": "FRED: HOUST",
      "date": "January 2026",
      "geography": "United States",
      "trend": "Fluctuating, with recent increase from previous month."
    },
    {
      "metric_name": "Building Permits: Total Units",
      "value": "1,376,000 units (annualized)",
      "source": "FRED: PERMIT",
      "date": "January 2026",
      "geography": "United States",
      "trend": "Fluctuating, with recent decrease from previous month."
    },
    {
      "metric_name": "Rental Vacancy Rate",
      "value": "7.2%",
      "source": "FRED: RRVRUSQ156N",
      "date": "Q4 2025 (October)",
      "geography": "United States",
      "trend": "Slight upward trend over the past year, indicating a loosening rental market nationally."
    },
    {
      "metric_name": "Construction Employment",
      "value": "8,011,000 employees",
      "source": "BLS: CEU2000000001",
      "date": "February 2026",
      "geography": "United States",
      "trend": "Slight decrease from peak levels in late 2025, but generally stable."
    },
    {
      "metric_name": "Construction Average Hourly Wages",
      "value": "$40.66/hour",
      "source": "BLS: CEU2000000003",
      "date": "February 2026",
      "geography": "United States",
      "trend": "Steady upward trend."
    }
  ],
  "demand_metrics": [
    {
      "metric_name": "Total Population",
      "value": "343,157,450",
      "source": "FRED: POP",
      "date": "December 2025",
      "geography": "United States",
      "trend": "Steady increase."
    },
    {
      "metric_name": "Real Median Household Income",
      "value": "$83,730",
      "source": "FRED: MEHOINUSA672N",
      "date": "2024",
      "geography": "United States",
      "trend": "Upward trend since 2022."
    },
    {
      "metric_name": "30-Year Fixed Rate Mortgage Average",
      "value": "6.22%",
      "source": "FRED: MORTGAGE30US",
      "date": "March 19, 2026",
      "geography": "United States",
      "trend": "Fluctuating, with a recent slight increase."
    },
    {
      "metric_name": "Homeownership Rate",
      "value": "65.7%",
      "source": "FRED: RHORUSQ156N",
      "date": "Q4 2025 (October)",
      "geography": "United States",
      "trend": "Relatively stable over the past year."
    }
  ],
  "price_metrics": [
    {
      "metric_name": "Median Gross Rent",
      "value": "$1,268/month",
      "source": "Census ACS 2022, Table B25064_001E",
      "date": "2022",
      "geography": "United States",
      "trend": "Generally increasing (inferred from CPI-Rent)."
    },
    {
      "metric_name": "Median Sales Price of Houses Sold",
      "value": "$405,300",
      "source": "FRED: MSPUS",
      "date": "Q4 2025 (October)",
      "geography": "United States",
      "trend": "Fluctuating, with a recent slight decrease."
    },
    {
      "metric_name": "CPI: Rent of Primary Residence",
      "value": "441.865 (Index 1982-1984=100)",
      "source": "FRED: CUSR0000SEHA",
      "date": "February 2026",
      "geography": "U.S. City Average",
      "trend": "Steady upward trend."
    },
    {
      "metric_name": "Estimated Median Rent-to-Income Ratio",
      "value": "19.14%",
      "source": "Calculated from Census ACS 2022 Median Gross Rent ($1268/month) and FRED 2022 Real Median Household Income ($79,500/year)",
      "date": "2022",
      "geography": "United States",
      "trend": "N/A (single data point)"
    }
  ],
  "sub_markets": [],
  "overall_tightness": "Moderate. The national rental vacancy rate of 7.2% suggests a balanced market, but this is an aggregate. Housing starts and permits show some volatility. Home prices and rents have generally been increasing, though home prices have seen recent fluctuations. The estimated median rent-to-income ratio of 19.14% suggests affordability for the median household, but this masks significant burdens for lower-income households and in high-cost regions.",
  "data_gaps": [
    "Detailed, current national median rent-to-income ratio (beyond a simple median calculation).",
    "Specific sub-market assessments (e.g., 'very tight' vs. 'loose' metros) would require selecting and analyzing individual metropolitan areas or counties, which is beyond the scope of a national baseline. This would involve pulling local vacancy rates, price trends, and rent-to-income ratios for selected representative geographies."
  ]
}
```
