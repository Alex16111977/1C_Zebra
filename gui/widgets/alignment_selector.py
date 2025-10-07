# -*- coding: utf-8 -*-
"""Віджет вирівнювання тексту"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QToolButton, QButtonGroup
from PySide6.QtCore import Signal

from core.enums import TextAlignment
from utils.logger import logger


class AlignmentSelector(QWidget):
    """Кнопки вирівнювання"""

    alignmentChanged = Signal(TextAlignment)

    def __init__(self):
        super().__init__()
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self._button_alignment = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for alignment in TextAlignment:
            btn = QToolButton(self)
            btn.setCheckable(True)
            btn.setText(alignment.display_name[0])
            btn.setToolTip(f"Align {alignment.display_name}")
            self.button_group.addButton(btn)
            self._button_alignment[btn] = alignment
            layout.addWidget(btn)
            if alignment == TextAlignment.LEFT:
                btn.setChecked(True)

        self.button_group.buttonClicked.connect(self._on_clicked)
        logger.debug("[ALIGN-SELECTOR] Initialized")

    def _on_clicked(self, button):
        alignment = self._button_alignment.get(button, TextAlignment.LEFT)
        logger.debug(f"[ALIGN-SELECTOR] Selected alignment: {alignment.key}")
        self.alignmentChanged.emit(alignment)

    def set_alignment(self, alignment: TextAlignment):
        for button, current_alignment in self._button_alignment.items():
            if current_alignment == alignment:
                button.setChecked(True)
                return
        logger.warning(f"[ALIGN-SELECTOR] Alignment {alignment} not found")

    def current_alignment(self) -> TextAlignment:
        button = self.button_group.checkedButton()
        return self._button_alignment.get(button, TextAlignment.LEFT)
