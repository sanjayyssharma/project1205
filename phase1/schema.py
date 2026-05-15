"""Canonical restaurant model and raw Hugging Face column names."""

from __future__ import annotations

from typing import Final, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

# Column names as published on Hugging Face (ManikaSaini/zomato-restaurant-recommendation).
RAW_URL: Final = "url"
RAW_ADDRESS: Final = "address"
RAW_NAME: Final = "name"
RAW_ONLINE_ORDER: Final = "online_order"
RAW_BOOK_TABLE: Final = "book_table"
RAW_RATE: Final = "rate"
RAW_VOTES: Final = "votes"
RAW_PHONE: Final = "phone"
RAW_LOCATION: Final = "location"
RAW_REST_TYPE: Final = "rest_type"
RAW_DISH_LIKED: Final = "dish_liked"
RAW_CUISINES: Final = "cuisines"
RAW_APPROX_COST: Final = "approx_cost(for two people)"
RAW_REVIEWS_LIST: Final = "reviews_list"
RAW_MENU_ITEM: Final = "menu_item"
RAW_LISTED_IN_TYPE: Final = "listed_in(type)"
RAW_LISTED_IN_CITY: Final = "listed_in(city)"


class Restaurant(BaseModel):
    """Stable internal shape for filtering, prompts, and UI (Phase 2+)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Stable id assigned after ingest + dedupe ordering.")
    name: str
    locality: str = Field(description="Neighborhood / locality from the `location` column.")
    city_area: str = Field(
        description="Broader listing area from `listed_in(city)` (may differ from locality)."
    )
    cuisines: Tuple[str, ...] = Field(description="Trimmed cuisine tokens in display order.")
    rating: Optional[float] = Field(default=None, description="Parsed numeric rating when available.")
    votes: Optional[int] = None
    cost_for_two_inr: Optional[int] = Field(
        default=None,
        description="Approximate cost for two in INR when parsable.",
    )
    address: str = ""
    url: str = ""
    phone: str = ""
    rest_type: str = ""
    dish_liked: str = ""
    menu_item: str = ""
    online_order: str = ""
    book_table: str = ""
    listed_in_type: str = ""
