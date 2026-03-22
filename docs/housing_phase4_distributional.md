# Housing Phase 4: Distributional & Temporal

```json
{
  "by_tenure": {
    "Renters": [
      "Experience a net real income gain of +$1000.00 (UBI) minus housing cost increases.",
      "Net real income gain: +$917.45/month (low), +$872.57/month (central), +$812.59/month (high).",
      "Median gross rent increases by +$82.55 (low), +$127.43 (central), +$187.41 (high) per month."
    ],
    "Homeowners (Prospective Buyers)": [
      "Reduced home purchasing power due to assumed interest rate increases.",
      "Affordable home price reduction: -$10,132.50 (low), -$20,265.00 (central), -$40,530.00 (high).",
      "This is a separate affordability concern and not included in monthly net real income calculations."
    ],
    "Homeowners (Existing, Fixed-Rate Mortgage)": [
      "Minimal direct impact on monthly housing payments.",
      "Potential indirect impact on home equity due to market shifts, but not directly quantified here.",
      "No direct UBI offset by increased mortgage costs unless refinancing or moving."
    ]
  },
  "by_income": [
    {
      "income_level": "$35K/year",
      "tenure": "Renter",
      "monthly_housing_cost_change": "+$127.43",
      "housing_cost_share_before": "43.48%",
      "housing_cost_share_after": "35.63%",
      "crosses_burden_threshold": true,
      "net_income_effect": "+$872.57"
    },
    {
      "income_level": "$55K/year",
      "tenure": "Renter",
      "monthly_housing_cost_change": "+$127.43",
      "housing_cost_share_before": "27.67%",
      "housing_cost_share_after": "25.00%",
      "crosses_burden_threshold": false,
      "net_income_effect": "+$872.57"
    },
    {
      "income_level": "$85K/year",
      "tenure": "Renter",
      "monthly_housing_cost_change": "+$127.43",
      "housing_cost_share_before": "17.90%",
      "housing_cost_share_after": "17.26%",
      "crosses_burden_threshold": false,
      "net_income_effect": "+$872.57"
    }
  ],
  "by_geography": {
    "Supply-Constrained Markets": [
      "Likely to experience the higher end of rent increases, especially from Pathway F (amplification in supply-constrained markets).",
      "Higher rent elasticity and lower vacancy rates will exacerbate price pressures.",
      "Examples: Major coastal cities, areas with restrictive zoning."
    ],
    "Markets with Moderate/Elastic Supply": [
      "May experience rent increases closer to the lower or central estimates.",
      "Higher vacancy rates (like the national 7.2%) and more responsive construction could temper price growth.",
      "Examples: Regions with ample developable land and fewer regulatory barriers."
    ],
    "Overall National Impact": [
      "The national rental vacancy rate of 7.2% suggests a balanced market on average, but masks significant regional variations.",
      "The aggregate impact is a general upward pressure on rents across all markets, with varying magnitudes."
    ]
  },
  "by_household_type": {},
  "temporal_sequence": [
    {
      "horizon": "0-6 months (Short-term)",
      "description": "Immediate increase in disposable income from UBI leads to heightened rental demand pressure on a fixed supply.",
      "dominant_channel": "Demand pressure, Pathway B (income elasticity)",
      "magnitude": "Initial rent increases, estimated at 5.01% (low) to 7.88% (high) or +$63.54 to +$99.93 per month.",
      "uncertainty": "MEDIUM"
    },
    {
      "horizon": "6-18 months (Short-medium term)",
      "description": "Lease renewals allow landlords to adjust prices. Operating cost pass-through begins to manifest.",
      "dominant_channel": "Lease renewals, Pathway B (full realization), Pathway C (landlord operating costs)",
      "magnitude": "Continued rent increases, with Pathway C adding 0.5% (low) to 2.4% (high) or +$6.34 to +$30.43 per month.",
      "uncertainty": "MEDIUM"
    },
    {
      "horizon": "18-36 months (Medium term)",
      "description": "Amplification in supply-constrained markets, initial construction cost adjustments, and migration shifts become more apparent. Home purchasing power begins to decline.",
      "dominant_channel": "Pathway F (supply-constrained markets), Pathway A (construction costs), Pathway E (migration), Pathway D (home purchasing power)",
      "magnitude": "Further rent increases (Pathway F: +0.5% to +2.0%; Pathway A: +0.3% to +1.5%; Pathway E: +0.2% to +1.0%). Home purchasing power reduced by 2.5% (low) to 10.0% (high).",
      "uncertainty": "MEDIUM"
    },
    {
      "horizon": "3-5+ years (Long-term)",
      "description": "Potential for supply response (if construction accelerates). Full impact of all pathways, including sustained reduction in home purchasing power.",
      "dominant_channel": "Supply equilibrium (or lack thereof), full realization of all pathways (A, C, E, F), sustained Pathway D",
      "magnitude": "Rent increases stabilize at a higher level, potentially offset by new supply. Home affordability remains significantly reduced, with a total rent increase of +$82.55 to +$187.41 per month.",
      "uncertainty": "HIGH"
    }
  ],
  "computation_notes": [
    "All dollar figures for rent increases are based on a $1,268/month (2022) baseline median gross rent, which is noted as likely conservative for 2026.",
    "For 'By Income' calculations, a central estimate of total monthly rent increase (+$127.43) was used for simplicity and consistency across income tiers.",
    "Income tiers assume the household receives the full $1,000/month UBI.",
    "The 30% housing burden threshold is a common standard for affordability.",
    "Impacts on homeowners with existing fixed-rate mortgages are considered minimal in terms of direct monthly payment changes, but prospective buyers face significant affordability challenges.",
    "Geographical impacts are qualitative due to the national scope of the input data, highlighting differences between supply-constrained and more elastic markets."
  ]
}
```
