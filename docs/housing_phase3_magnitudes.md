# Housing Phase 3: Magnitude Estimates

```json
{
  "estimates": [
    {
      "pathway_id": "B",
      "metric": "Percentage increase in median gross rent",
      "low_estimate": "5.01%",
      "central_estimate": "6.45%",
      "high_estimate": "7.88%",
      "methodology": "Calculated as the percentage increase in median household income ($12,000 UBI / $83,730 baseline income = 14.33%) multiplied by the rent elasticity with respect to income. Elasticity range (0.3-0.7) adjusted for moderate market tightness (7.2% vacancy rate) to 0.35 (low), 0.45 (central), 0.55 (high).",
      "time_horizon": "Short to medium term (1-3 years)",
      "geography": "National",
      "assumptions": [
        "UBI is widely adopted and directly increases household income.",
        "The chosen income elasticities accurately reflect market response given moderate tightness.",
        "Median household income is representative for calculating the percentage income increase."
      ]
    },
    {
      "pathway_id": "B",
      "metric": "Dollar increase in median gross rent per month",
      "low_estimate": "$63.54/month",
      "central_estimate": "$81.79/month",
      "high_estimate": "$99.93/month",
      "methodology": "Derived from the percentage rent increases for Pathway B, applied to the baseline median gross rent of $1,268/month (2022).",
      "time_horizon": "Short to medium term (1-3 years)",
      "geography": "National",
      "assumptions": [
        "UBI is widely adopted and directly increases household income.",
        "The chosen income elasticities accurately reflect market response given moderate tightness.",
        "Median gross rent of $1,268/month (2022) serves as a reasonable base for dollar impact calculation, acknowledging it may be higher in 2026."
      ]
    },
    {
      "pathway_id": "D",
      "metric": "Percentage reduction in home purchasing power",
      "low_estimate": "2.5%",
      "central_estimate": "5.0%",
      "high_estimate": "10.0%",
      "methodology": "Assumed increase in interest rates (0.25pp low, 0.50pp central, 1.00pp high) due to fiscal stimulus, multiplied by the mortgage rate sensitivity (1pp rate increase → ~10% purchasing power reduction).",
      "time_horizon": "Medium to long term (1-5 years)",
      "geography": "National",
      "assumptions": [
        "The UBI policy leads to the specified increases in interest rates.",
        "The mortgage rate sensitivity of 10% reduction per 1pp increase is constant.",
        "This impact primarily affects potential home buyers."
      ]
    },
    {
      "pathway_id": "D",
      "metric": "Dollar reduction in affordable home price",
      "low_estimate": "$10,132.50",
      "central_estimate": "$20,265.00",
      "high_estimate": "$40,530.00",
      "methodology": "Derived from the percentage reduction in home purchasing power for Pathway D, applied to the baseline median sales price of houses sold ($405,300 in Q4 2025).",
      "time_horizon": "Medium to long term (1-5 years)",
      "geography": "National",
      "assumptions": [
        "The UBI policy leads to the specified increases in interest rates.",
        "The mortgage rate sensitivity of 10% reduction per 1pp increase is constant.",
        "Median sales price is representative for calculating the dollar impact on affordability."
      ]
    },
    {
      "pathway_id": "F",
      "metric": "Additional percentage increase in median gross rent due to amplification",
      "low_estimate": "0.5%",
      "central_estimate": "1.0%",
      "high_estimate": "2.0%",
      "methodology": "Estimated additional rent increase on top of direct demand effects (Pathway B), reflecting the amplification of price/rent increases in supply-constrained markets due to land use regulations or rent control. This is a direct estimate of the additional pressure.",
      "time_horizon": "Medium term (2-4 years)",
      "geography": "Primarily in supply-constrained urban/suburban markets, aggregated nationally",
      "assumptions": [
        "UBI-driven demand interacts with existing regulatory barriers to create additional upward pressure beyond direct demand.",
        "The estimated percentages represent the aggregate additional impact across various constrained markets."
      ]
    },
    {
      "pathway_id": "F",
      "metric": "Additional dollar increase in median gross rent per month due to amplification",
      "low_estimate": "$6.34/month",
      "central_estimate": "$12.68/month",
      "high_estimate": "$25.36/month",
      "methodology": "Derived from the additional percentage rent increases for Pathway F, applied to the baseline median gross rent of $1,268/month (2022).",
      "time_horizon": "Medium term (2-4 years)",
      "geography": "Primarily in supply-constrained urban/suburban markets, aggregated nationally",
      "assumptions": [
        "UBI-driven demand interacts with existing regulatory barriers to create additional upward pressure beyond direct demand.",
        "Median gross rent of $1,268/month (2022) serves as a reasonable base for dollar impact calculation."
      ]
    },
    {
      "pathway_id": "A",
      "metric": "Percentage increase in median gross rent",
      "low_estimate": "0.3%",
      "central_estimate": "0.8%",
      "high_estimate": "1.5%",
      "methodology": "Assumed increase in construction costs (1% low, 2% central, 3% high) due to UBI-driven demand for labor and materials, multiplied by the construction cost pass-through to rent (0.3 low, 0.4 central, 0.5 high).",
      "time_horizon": "Long-run (3-5+ years)",
      "geography": "National",
      "assumptions": [
        "UBI leads to specified increases in construction costs.",
        "The long-run pass-through rates for construction costs to rent are accurate."
      ]
    },
    {
      "pathway_id": "A",
      "metric": "Dollar increase in median gross rent per month",
      "low_estimate": "$3.80/month",
      "central_estimate": "$10.14/month",
      "high_estimate": "$19.02/month",
      "methodology": "Derived from the percentage rent increases for Pathway A, applied to the baseline median gross rent of $1,268/month (2022).",
      "time_horizon": "Long-run (3-5+ years)",
      "geography": "National",
      "assumptions": [
        "UBI leads to specified increases in construction costs.",
        "Median gross rent of $1,268/month (2022) serves as a reasonable base for dollar impact calculation."
      ]
    },
    {
      "pathway_id": "C",
      "metric": "Percentage increase in median gross rent",
      "low_estimate": "0.5%",
      "central_estimate": "1.3%",
      "high_estimate": "2.4%",
      "methodology": "Assumed increase in landlord operating costs (1% low, 2% central, 3% high) due to general inflation or wage pressure from UBI, multiplied by the operating cost pass-through to rent (50% low, 65% central, 80% high).",
      "time_horizon": "Short to medium term (1-2 years)",
      "geography": "National",
      "assumptions": [
        "UBI leads to specified increases in landlord operating costs.",
        "The pass-through rates for operating costs to rent are accurate within the specified timeframe."
      ]
    },
    {
      "pathway_id": "C",
      "metric": "Dollar increase in median gross rent per month",
      "low_estimate": "$6.34/month",
      "central_estimate": "$16.48/month",
      "high_estimate": "$30.43/month",
      "methodology": "Derived from the percentage rent increases for Pathway C, applied to the baseline median gross rent of $1,268/month (2022).",
      "time_horizon": "Short to medium term (1-2 years)",
      "geography": "National",
      "assumptions": [
        "UBI leads to specified increases in landlord operating costs.",
        "Median gross rent of $1,268/month (2022) serves as a reasonable base for dollar impact calculation."
      ]
    },
    {
      "pathway_id": "E",
      "metric": "Additional percentage increase in median gross rent due to migration shifts",
      "low_estimate": "0.2%",
      "central_estimate": "0.5%",
      "high_estimate": "1.0%",
      "methodology": "Estimated additional rent increase reflecting localized demand pressures from UBI enabling shifts in population flows to previously less attractive or lower-cost regions, or sustaining demand in higher-cost areas.",
      "time_horizon": "Medium to long term (2-5 years)",
      "geography": "Regional/National (aggregate of regional shifts)",
      "assumptions": [
        "UBI provides sufficient financial flexibility to influence migration decisions.",
        "These shifts lead to measurable localized demand increases that aggregate to a national impact."
      ]
    },
    {
      "pathway_id": "E",
      "metric": "Additional dollar increase in median gross rent per month due to migration shifts",
      "low_estimate": "$2.54/month",
      "central_estimate": "$6.34/month",
      "high_estimate": "$12.68/month",
      "methodology": "Derived from the additional percentage rent increases for Pathway E, applied to the baseline median gross rent of $1,268/month (2022).",
      "time_horizon": "Medium to long term (2-5 years)",
      "geography": "Regional/National (aggregate of regional shifts)",
      "assumptions": [
        "UBI provides sufficient financial flexibility to influence migration decisions.",
        "Median gross rent of $1,268/month (2022) serves as a reasonable base for dollar impact calculation."
      ]
    }
  ],
  "key_elasticities_used": {
    "Rent elasticity w.r.t. income": "0.3 (loose markets) to 0.7 (tight markets) - adjusted to 0.35-0.55 for moderate market tightness.",
    "Construction cost pass-through to rent": "1% cost increase → 0.3-0.5% rent increase (long-run).",
    "Operating cost pass-through to rent": "50-80% within 12-18 months.",
    "Mortgage rate sensitivity": "1pp rate increase → ~10% purchasing power reduction."
  },
  "nominal_vs_real_analysis": "The universal basic income provides a nominal increase of $1000 per month. However, this nominal gain is partially offset by increases in housing costs (primarily rent) across various channels. The net real income change, after accounting for these housing cost increases, is estimated as follows:\n-   **Low Estimate:** $1000 (UBI) - $82.55 (Total Housing Cost Increase) = $917.45/month\n-   **Central Estimate:** $1000 (UBI) - $127.43 (Total Housing Cost Increase) = $872.57/month\n-   **High Estimate:** $1000 (UBI) - $187.41 (Total Housing Cost Increase) = $812.59/month\n\nThis analysis indicates that while the UBI provides a significant nominal income boost, a portion of it will be absorbed by increased housing expenses, leading to a lower, but still substantial, net real income gain for recipients, particularly those who rent. The impact on home buyers' purchasing power (Pathway D) is a separate but related affordability concern.",
  "computation_notes": [
    "Median gross rent from 2022 ($1,268/month) was used as the base for dollar calculations due to the lack of a more current national median rent figure. Given the upward trend in CPI for rent, actual current median rent is likely higher, meaning the dollar increases calculated might be conservative if applied to 2026 rent levels.",
    "The 'moderate' market tightness (7.2% rental vacancy rate) informed the selection of elasticity values, generally leaning towards the lower end of the provided ranges for 'loose markets' but not the absolute minimum.",
    "Pathways F (Land Use/Regulatory Interaction) and E (Migration/Location Choice) are quantified as 'additional' percentage increases in rent, reflecting their role in amplifying or redistributing demand pressures beyond the direct income effect.",
    "The impact of Pathway D (Interest Rate/Financing) is presented as a reduction in home purchasing power for buyers and is not directly aggregated into the 'housing cost change' for the net real income calculation, which focuses on monthly housing expenses (rent). However, higher interest rates could indirectly shift demand towards the rental market, exacerbating rental price pressures."
  ]
}
```
