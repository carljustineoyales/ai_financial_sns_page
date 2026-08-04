"""render_month_calendar: a Sun-Sat month grid with per-day event chips."""

import calendar as calendar_module

from PIL import Image, ImageDraw

from .primitives import _draw_chip, _draw_title_header, _draw_watermark_inline, _font, _load_logo, _truncate_to_width
from .theme import (
    BACKGROUND,
    BODY_FOOTER_GAP,
    CHIP_HEIGHT,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HEADER_BG,
    HEADER_TEXT,
    HEIGHT,
    LOGO_GAP,
    PADDING,
    ROW_ALT_BG,
    ROW_TEXT,
    RULE_COLOR,
    SECTION_RULE_COLOR,
    SUBTITLE_COLOR,
    TITLE_BLOCK_HEIGHT,
    TITLE_COLOR,
    WEEKDAY_LABELS,
    WIDTH,
)


def render_month_calendar(year, month, events_by_day, title, subtitle, footer_lines, output_path, max_events_per_day=3):
    """Renders a Sun-Sat month grid to a fixed WIDTHxHEIGHT PNG (Facebook's
    recommended feed image size), each day cell showing the day number and
    up to max_events_per_day events (ticker as plain text, event-type code
    as a color-coded rounded chip beside it), with a "+N more" line if
    there are more. events_by_day: {day_of_month (int): [(symbol,
    chip_text, color), ...]}. max_events_per_day is a ceiling -- the actual
    number shown may be lower if the fixed canvas leaves less room (a
    6-week month has less height per cell than a 5-week month).
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    weekday_font = _font("DejaVuSans-Bold.ttf", 16)
    day_num_font = _font("DejaVuSans-Bold.ttf", 18)
    event_font = _font("DejaVuSans.ttf", 13)
    footer_font = _font("DejaVuSans.ttf", 15)

    weeks = calendar_module.Calendar(firstweekday=6).monthdayscalendar(year, month)

    grid_width = WIDTH - 2 * PADDING
    col_width = grid_width // 7
    weekday_header_height = 36
    event_line_height = 17

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    grid_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - weekday_header_height - footer_height - FOOTER_BOTTOM_MARGIN - BODY_FOOTER_GAP
    cell_height = grid_height // len(weeks)

    day_number_height = 26
    max_events_that_fit = max(0, (cell_height - day_number_height - 6) // event_line_height)
    max_events_per_day = min(max_events_per_day, max_events_that_fit)

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    draw.rounded_rectangle([PADDING, y, WIDTH - PADDING, y + weekday_header_height], radius=8, fill=HEADER_BG)
    for i, label in enumerate(WEEKDAY_LABELS):
        cx = PADDING + i * col_width
        draw.text((cx + 10, y + 8), label, font=weekday_font, fill=HEADER_TEXT)
    y += weekday_header_height

    for week in weeks:
        for i, day in enumerate(week):
            cx = PADDING + i * col_width
            draw.rectangle([cx, y, cx + col_width, y + cell_height], outline=RULE_COLOR, width=1, fill=ROW_ALT_BG)
            if day == 0:
                continue

            draw.text((cx + 8, y + 6), str(day), font=day_num_font, fill=TITLE_COLOR)

            day_events = events_by_day.get(day, [])
            shown = day_events[:max_events_per_day]
            ey = y + 6 + 22
            for symbol, chip_text, chip_color in shown:
                chip_width = _draw_chip(image, draw, cx + 8, ey, chip_text, event_font, chip_color)
                logo = _load_logo(symbol, CHIP_HEIGHT)
                logo_offset = CHIP_HEIGHT + LOGO_GAP if logo else 0
                if logo:
                    image.paste(logo, (int(cx + 8 + chip_width + 6), int(ey)), logo)
                symbol_x = cx + 8 + chip_width + 6 + logo_offset
                symbol_max_width = col_width - 16 - chip_width - 6 - logo_offset
                symbol_text = _truncate_to_width(draw, symbol, event_font, symbol_max_width)
                draw.text((symbol_x, ey), symbol_text, font=event_font, fill=ROW_TEXT)
                ey += event_line_height

            remaining = len(day_events) - max_events_per_day
            if remaining > 0:
                draw.text((cx + 8, ey), f"+{remaining} more", font=event_font, fill=SUBTITLE_COLOR)
        y += cell_height

    footer_y = HEIGHT - FOOTER_BOTTOM_MARGIN - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=SECTION_RULE_COLOR, width=2)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark_inline(draw, fy - FOOTER_LINE_HEIGHT)
    image.save(output_path, "PNG")
    return output_path
