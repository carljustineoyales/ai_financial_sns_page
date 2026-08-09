"""Layout constants and palette for the rendering package.

Deliberately simple -- these are Facebook utility graphics (dividend
schedules, etc.), not polished design artifacts. Uses DejaVu Sans, which
ships system-wide on this machine, so no font file needs to be bundled --
DESIGN.md's own font-substitute note names Inter as the closest open
substitute for Geist Sans, and DejaVu Sans (a similar humanist grotesque)
stands in for that without requiring a bundled font file.
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

# Palette follows DESIGN.md's Vercel-Geist system (single canvas mode --
# the doc doesn't define a dark theme, so there's no light/dark switch).
# Functional status colors (paid/upcoming/passed chips, trading-style
# up/down cues) aren't part of the brand palette -- DESIGN.md's own
# "Semantic" section only defines Error/Warning plus "Success maps to
# {colors.link}" (no distinct green), so a couple of these still need
# independent, non-brand hues to stay genuinely distinguishable at a
# glance; where Geist *does* define a matching semantic token (Error,
# Link) those are used directly instead of an arbitrary hex.
ACCENT = "#0070f3"  # Vercel Blue -- Geist's only chromatic accent; "primary" merges into ink itself, no separate CTA color exists
TRADING_UP = "#0ecb81"  # independent, non-brand -- Geist has no green; financial up/positive needs a real one
TRADING_DOWN = "#ee0000"  # Geist's own Error red -- doubles as the financial down/negative cue
INFO = ACCENT  # Geist: "Success maps to {colors.link}" -- the same blue is both accent and positive/active signal

CANVAS = "#fafafa"
CANVAS_SOFT = "#f2f2f2"  # Geist's hairline-soft: "faintest grey fill for subtle alternating panels and inset wells"
HAIRLINE = "#ebebeb"  # Geist's own token for "the 1px border on every card, input, and divider -- the structural workhorse"
MUTE = "#8f8f8f"
FAINT = "#a1a1a1"
BODY = "#4d4d4d"
INK_MID = BODY  # Geist's 4-step ladder (ink/body/mute/faint) has no separate mid-emphasis tier
INK_SOFT = "#171717"
INK = "#171717"
BODY_MID = MUTE  # Geist's own "lower-emphasis captions... metadata" role

BACKGROUND = CANVAS
TITLE_COLOR = INK
SUBTITLE_COLOR = BODY_MID
HEADER_BG = CANVAS_SOFT
HEADER_TEXT = INK
ROW_TEXT = INK
ROW_ALT_BG = CANVAS_SOFT
RULE_COLOR = HAIRLINE
SECTION_RULE_COLOR = HAIRLINE
FOOTER_COLOR = BODY
CHIP_TINT_BASE = CANVAS_SOFT
# DESIGN.md: "the one place color is allowed to exist is the hero...
# everywhere else, restraint" -- a corner signature isn't a link, pricing
# highlight, or focus signal, so it stays muted ink rather than accent.
WATERMARK_TEXT_COLOR = MUTE

# DESIGN.md: "{rounded.md} 12px -- feature cards, code blocks" -- same
# 12px value the old Zapier system also used, so this didn't need to
# change even though the underlying brand did.
RADIUS_CARD = 12

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

ASSETS_LOGO_DIR = os.path.join("assets", "logos")

WATERMARK_TEXT = "Purrfolio"
WATERMARK_COLOR = WATERMARK_TEXT_COLOR

# Trading-semantic status colors: PAID reuses trading-up green (settled,
# positive), UPCOMING reuses info/accent blue (neutral/future), EX-DATE
# PASSED stays a neutral muted tone rather than the accent blue -- the
# accent is reserved for the wordmark and small emphasis per DESIGN.md,
# not repeated per-row status borders.
STATUS_COLORS = {
    "PAID": TRADING_UP,
    "EX-DATE PASSED": BODY_MID,
    "UPCOMING": INFO,
}

CHIP_PADDING_X = 6
CHIP_HEIGHT = 16
LOGO_GAP = 4

COMPANY_DIRECTORY_CACHE = os.path.join("data", "pse_companies.json")
