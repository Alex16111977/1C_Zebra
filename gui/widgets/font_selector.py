# -*- coding: utf-8 -*-
"""Віджет вибору ZPL шрифту"""

from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Signal

from core.enums import ZplFont
from utils.logger import logger


class FontSelector(QComboBox):
    """Комбо-бокс зі списком шрифтів ZPL"""

    fontChanged = Signal(ZplFont)

    def __init__(self):
        super().__init__()
        self._populate()
        self.currentIndexChanged.connect(self._on_changed)
        logger.debug("[FONT-SELECTOR] Initialized")

    def _populate(self):
        """Заповнити список шрифтів"""
        self.clear()
        for font in ZplFont:
            self.addItem(font.display_name, font)
        self.setCurrentIndex(0)

    def _on_changed(self, index: int):
        font = self.itemData(index)
        if isinstance(font, ZplFont):
            logger.debug(f"[FONT-SELECTOR] Selected font: {font.code} - {font.display_name}")
            self.fontChanged.emit(font)

    def current_font(self) -> ZplFont:
        font = self.currentData()
        return font if isinstance(font, ZplFont) else ZplFont.SCALABLE

    def set_font(self, font: ZplFont):
        for idx in range(self.count()):
            if self.itemData(idx) == font:
                self.setCurrentIndex(idx)
                return
        logger.warning(f"[FONT-SELECTOR] Font {font} not found, fallback to default")
        self.setCurrentIndex(0)
