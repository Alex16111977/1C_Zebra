# -*- coding: utf-8 -*-
"""Віджет вибору точки прив'язки"""

from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QButtonGroup
from PySide6.QtCore import Signal

from core.enums import AnchorPosition
from utils.logger import logger


class AnchorSelector(QWidget):
    """3x3 кнопки для вибору anchor"""

    anchorChanged = Signal(AnchorPosition)

    def __init__(self):
        super().__init__()
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self._button_anchor = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)

        for row in range(3):
            for col in range(3):
                anchor_value = row * 3 + col
                anchor = AnchorPosition(anchor_value)
                btn = QPushButton("", self)
                btn.setCheckable(True)
                btn.setFixedSize(26, 26)
                self.button_group.addButton(btn)
                self._button_anchor[btn] = anchor
                grid.addWidget(btn, row, col)

                style_parts = []
                if row == 0:
                    style_parts.append("border-top: 1px solid #888;")
                if row == 2:
                    style_parts.append("border-bottom: 1px solid #888;")
                if col == 0:
                    style_parts.append("border-left: 1px solid #888;")
                if col == 2:
                    style_parts.append("border-right: 1px solid #888;")
                if anchor == AnchorPosition.CENTER:
                    style_parts.append("background-color: #f5f5f5;")
                btn.setStyleSheet("".join(style_parts))

                if anchor == AnchorPosition.TOP_LEFT:
                    btn.setChecked(True)

        self.button_group.buttonClicked.connect(self._on_clicked)
        logger.debug("[ANCHOR-SELECTOR] Initialized")

    def _on_clicked(self, button):
        anchor = self._button_anchor.get(button, AnchorPosition.TOP_LEFT)
        logger.debug(f"[ANCHOR-SELECTOR] Selected anchor: {anchor.name}")
        self.anchorChanged.emit(anchor)

    def set_anchor(self, anchor: AnchorPosition):
        for button, current_anchor in self._button_anchor.items():
            if current_anchor == anchor:
                button.setChecked(True)
                return
        logger.warning(f"[ANCHOR-SELECTOR] Anchor {anchor} not found")

    def current_anchor(self) -> AnchorPosition:
        button = self.button_group.checkedButton()
        return self._button_anchor.get(button, AnchorPosition.TOP_LEFT)
