"""Layout constants and palette for the rendering package.

Deliberately simple -- these are Facebook utility graphics (dividend
schedules, etc.), not polished design artifacts. Uses DejaVu Sans, which
ships system-wide on this machine, so no font file needs to be bundled --
DESIGN.md's own font-substitute note names Inter as the closest open
substitute for both of the brand's faces, and DejaVu Sans (a similar
humanist grotesque) stands in for that without requiring a bundled font
file.
"""

import os

WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

WIDTH = 1080
HEIGHT = 1080
PADDING = 40
ROW_HEIGHT = 50
HEADER_ROW_HEIGHT = 36
MAX_ROW_SCALE = 2.0
TITLE_BLOCK_HEIGHT = 110
FOOTER_LINE_HEIGHT = 28
# Breathing room reserved between body content and the footer rule,
# matching the gap _draw_title_header leaves between its rule and the
# body (header_bottom - 18) so both dividers read as the same kind of
# section break instead of the footer one sitting flush against content.
BODY_FOOTER_GAP = 18
# Bottom margin below the footer block. Smaller than the outer PADDING
# (used for the canvas's other three edges) because the watermark now
# shares the footer's last text line instead of occupying its own row
# below it -- see _draw_watermark_inline -- so the footer no longer needs
# PADDING-sized clearance underneath it.
FOOTER_BOTTOM_MARGIN = 24

# Palette follows DESIGN.md's warm-cream Zapier-style system (single
# canvas mode -- the doc doesn't define a dark theme, so the old
# light/dark THEME switch is dropped along with it). Functional status
# colors (paid/upcoming/passed chips, trading-style up/down cues) aren't
# part of the brand palette -- DESIGN.md's "Semantic" section explicitly
# says the brand borrows its ink/orange hierarchy instead of a status
# palette, but this app needs three genuinely distinguishable colors to
# tell dividend statuses apart at a glance, so those keep their own
# independent, non-brand hues.
PRIMARY_ORANGE = "#ff4f00"
TRADING_UP = "#0ecb81"
TRADING_DOWN = "#f6465d"
INFO = "#3b82f6"

CANVAS = "#fffefb"
CANVAS_SOFT = "#f8f4f0"
MUTE = "#c5c0b1"
BODY_MID = "#939084"
BODY = "#605d52"
INK_MID = "#36342e"
INK_SOFT = "#2f2a26"
INK = "#201515"

BACKGROUND = CANVAS
TITLE_COLOR = INK
SUBTITLE_COLOR = BODY_MID
HEADER_BG = CANVAS_SOFT
HEADER_TEXT = INK
ROW_TEXT = INK
ROW_ALT_BG = CANVAS_SOFT
RULE_COLOR = MUTE
SECTION_RULE_COLOR = BODY_MID
FOOTER_COLOR = BODY
CHIP_TINT_BASE = CANVAS_SOFT
WATERMARK_TEXT_COLOR = PRIMARY_ORANGE

# DESIGN.md: "{rounded.md} 12px for buttons and cards -- the brand's
# middle-radius signature", a single uniform radius rather than the old
# tiered small/medium/large scale.
RADIUS_CARD = 12

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

ASSETS_LOGO_DIR = os.path.join("assets", "logos")

WATERMARK_TEXT = "Neko Yields"
WATERMARK_COLOR = WATERMARK_TEXT_COLOR

# Trading-semantic status colors: PAID reuses trading-up green (settled,
# positive), UPCOMING reuses info blue (neutral/future), EX-DATE PASSED
# stays a neutral muted tone rather than primary yellow -- yellow is
# reserved for the single wordmark accent per DESIGN.md, not repeated
# per-row status borders.
STATUS_COLORS = {
    "PAID": TRADING_UP,
    "EX-DATE PASSED": BODY_MID,
    "UPCOMING": INFO,
}

CHIP_PADDING_X = 6
CHIP_HEIGHT = 16
LOGO_GAP = 4

COMPANY_DIRECTORY_CACHE = os.path.join("data", "pse_companies.json")
