"""Domain constants shared across layers.

Week convention: day_index 0 = Sunday ... 6 = Saturday (Israeli week).
Shifts are NOT constants — they are configured via the SHIFTS env var and
read from ``current_app.config`` (SHIFTS / SHIFT_NAMES / SHIFT_LABELS).
"""
from __future__ import annotations

# Hebrew day names, indexed 0=Sunday ... 6=Saturday.
DAY_NAMES_HE: tuple[str, ...] = (
    "ראשון",
    "שני",
    "שלישי",
    "רביעי",
    "חמישי",
    "שישי",
    "שבת",
)

# Pastel palette per day index (mirrors the reference sheet look).
DAY_COLORS: tuple[str, ...] = (
    "#e7eef7",  # ראשון  - light blue
    "#fde8da",  # שני    - peach
    "#d9efe4",  # שלישי  - mint
    "#dcecf6",  # רביעי  - sky
    "#e6e6f7",  # חמישי  - lavender
    "#fdf0d5",  # שישי   - cream
    "#d6efd9",  # שבת    - green
)
