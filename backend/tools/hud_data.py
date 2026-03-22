from __future__ import annotations

from backend.config import settings
from backend.tools._http import fetch_json
from backend.tools.schemas import HUDDataOutput

HUD_BASE_URL = "https://www.huduser.gov/hudapi/public"


async def hud_data(
    dataset: str,
    entity_id: str,
    year: int = 2025,
    quarter: int | None = None,
) -> HUDDataOutput:
    """Fetch housing data from HUD (Fair Market Rents, Income Limits, USPS vacancy).

    Args:
        dataset: "fmr" (Fair Market Rents), "il" (Income Limits), or "usps" (vacancy).
        entity_id: FIPS code (e.g. "5101399999" for Arlington) or state abbrev ("VA").
        year: Data year (default 2025).
        quarter: Quarter (1-4), only used for USPS vacancy data.
    """
    if dataset == "fmr":
        if len(entity_id) == 2:
            url = f"{HUD_BASE_URL}/fmr/statedata/{entity_id}"
        else:
            url = f"{HUD_BASE_URL}/fmr/data/{entity_id}"
    elif dataset == "il":
        if len(entity_id) == 2:
            url = f"{HUD_BASE_URL}/il/statedata/{entity_id}"
        else:
            url = f"{HUD_BASE_URL}/il/data/{entity_id}"
    elif dataset == "usps":
        url = f"{HUD_BASE_URL}/usps/{entity_id}"
        params_extra = {}
        if year:
            params_extra["year"] = str(year)
        if quarter:
            params_extra["quarter"] = str(quarter)
    else:
        return HUDDataOutput(
            dataset=dataset,
            entity_id=entity_id,
            data={"error": f"Unknown dataset: {dataset}. Use 'fmr', 'il', or 'usps'."},
        )

    # HUD API requires a Bearer token — skip gracefully if not configured
    if not settings.hud_data_api:
        return HUDDataOutput(
            dataset=dataset,
            entity_id=entity_id,
            data={"error": "HUD_DATA_API key not configured. Set it in .env to enable HUD queries."},
        )

    headers = {"Authorization": f"Bearer {settings.hud_data_api}"}

    # USPS has query params
    params = {}
    if dataset == "usps":
        params = params_extra

    raw = await fetch_json(url, params=params if params else None, headers=headers)

    return HUDDataOutput(
        dataset=dataset,
        entity_id=entity_id,
        data=raw,
    )
