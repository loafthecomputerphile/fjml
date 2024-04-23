from dataclasses import dataclass
from typing import Final

from flet import (
    Theme, TextThemeStyle, TextStyle,
    TextTheme, ScrollbarTheme, ThemeMode
)

class ThemeSettings:
    FONTS: dict[str, str] = {
        "DMSans": "/fonts/DMSans-VariableFont_opsz,wght.ttf"
    }
    
    MODE: Final[str] = "light"
    
    THEME: Theme = Theme(
        color_scheme_seed="green",
        text_theme=TextTheme(
            body_large=TextStyle(size=14, weight="w500", color="grey900"),
            body_medium=TextStyle(size=12, weight="w500", color="grey900"),
            body_small=TextStyle(size=10, weight="w500", color="grey900"),
            label_large=TextStyle(size=16, weight="w500", color="grey900"),
            label_medium=TextStyle(size=14, weight="w500", color="grey900"),
            label_small=TextStyle(size=12, weight="w500", color="grey900"),
            title_large=TextStyle(size=22, weight="w600", color="grey900"),
            title_medium=TextStyle(size=20, weight="w600", color="grey900"),
            title_small=TextStyle(size=18, weight="w600", color="grey900"),
            display_large=TextStyle(size=34, weight="w700", color="grey900"),
            display_medium=TextStyle(size=32, weight="w700", color="grey900"),
            display_small=TextStyle(size=30, weight="w700", color="grey900"),
            headline_large=TextStyle(size=28, weight="w700", color="grey900"),
            headline_medium=TextStyle(size=26, weight="w700", color="grey900"),
            headline_small=TextStyle(size=24, weight="w700", color="grey900")
        ),
        primary_text_theme=TextTheme(
            body_large=TextStyle(size=14, weight="w500", color="white"),
            body_medium=TextStyle(size=12, weight="w500", color="white"),
            body_small=TextStyle(size=10, weight="w500", color="white"),
            label_large=TextStyle(size=16, weight="w500", color="white"),
            label_medium=TextStyle(size=14, weight="w500", color="white"),
            label_small=TextStyle(size=12, weight="w500", color="white"),
            title_large=TextStyle(size=22, weight="w600", color="white"),
            title_medium=TextStyle(size=20, weight="w600", color="white"),
            title_small=TextStyle(size=18, weight="w600", color="white"),
            display_large=TextStyle(size=34, weight="w700", color="white"),
            display_medium=TextStyle(size=32, weight="w700", color="white"),
            display_small=TextStyle(size=30, weight="w700", color="white"),
            headline_large=TextStyle(size=28, weight="w700", color="white"),
            headline_medium=TextStyle(size=26, weight="w700", color="white"),
            headline_small=TextStyle(size=24, weight="w700", color="white")
        ),
        font_family="DMSans",
        scrollbar_theme=ScrollbarTheme(
            thickness=5,
            radius=4,
            # interactive=False,
        )
    )