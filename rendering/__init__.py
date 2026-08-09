"""Renders simple table-style graphic cards to PNG using Pillow.

Deliberately simple -- these are Facebook utility graphics (dividend
schedules, etc.), not polished design artifacts.
"""

from .theme import STATUS_COLORS, WIDTH, HEIGHT, PADDING, WATERMARK_TEXT
from .table import render_table_card
from .calendar import render_month_calendar
from .dividend_stamp import render_dividend_stamp_card
from .dividend_declaration_card import render_declaration_card
from .year_overview import render_year_overview
from .ticker_grid import render_ticker_logo_grid

__all__ = [
    "STATUS_COLORS",
    "WIDTH",
    "HEIGHT",
    "PADDING",
    "WATERMARK_TEXT",
    "render_table_card",
    "render_month_calendar",
    "render_dividend_stamp_card",
    "render_declaration_card",
    "render_year_overview",
    "render_ticker_logo_grid",
]
