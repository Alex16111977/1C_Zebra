# -*- coding: utf-8 -*-
"""Перечисления для розширених текстових можливостей"""

from enum import Enum
from typing import Optional


class ZplFont(Enum):
    """Внутрішні ZPL шрифти"""

    SCALABLE = ("0", "Scalable (Helvetica-like)", True, 0, 0)
    FONT_A = ("A", "Font A (9x5)", False, 9, 5)
    FONT_B = ("B", "Font B (11x7)", False, 11, 7)
    FONT_C = ("C", "Font C (18x10 Italic)", False, 18, 10)
    FONT_D = ("D", "Font D (18x10)", False, 18, 10)
    FONT_E = ("E", "Font E (28x15 OCR-B)", False, 28, 15)
    FONT_F = ("F", "Font F (26x13)", False, 26, 13)
    FONT_G = ("G", "Font G (60x40)", False, 60, 40)
    FONT_H = ("H", "Font H (34x22 OCR-A)", False, 34, 22)

    def __init__(self, code: str, display_name: str, scalable: bool, base_width: int, base_height: int):
        self.code = code
        self.display_name = display_name
        self.scalable = scalable
        self.base_width = base_width
        self.base_height = base_height

    @staticmethod
    def by_code(code: str) -> "ZplFont":
        """Повернути перерахування за кодом"""
        for font in ZplFont:
            if font.code == code:
                return font
        return ZplFont.SCALABLE


class TextAlignment(Enum):
    """Вирівнювання тексту"""

    LEFT = ("left", "L", "Left")
    CENTER = ("center", "C", "Center")
    RIGHT = ("right", "R", "Right")
    JUSTIFIED = ("justified", "J", "Justified")

    def __init__(self, key: str, zpl_code: str, display_name: str):
        self.key = key
        self.zpl_code = zpl_code
        self.display_name = display_name

    @staticmethod
    def from_key(key: Optional[str]) -> "TextAlignment":
        """Отримати alignment за ключем"""
        if not key:
            return TextAlignment.LEFT
        for alignment in TextAlignment:
            if alignment.key == key:
                return alignment
        return TextAlignment.LEFT


class AnchorPosition(Enum):
    """9-позиційна система якорів"""

    TOP_LEFT = 0
    TOP_CENTER = 1
    TOP_RIGHT = 2
    CENTER_LEFT = 3
    CENTER = 4
    CENTER_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_CENTER = 7
    BOTTOM_RIGHT = 8
