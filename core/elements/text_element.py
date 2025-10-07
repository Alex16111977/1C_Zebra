# -*- coding: utf-8 -*-
"""Текстовый елемент етикетки"""

from dataclasses import dataclass
from typing import Optional

from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QFont, QPen, QColor, QBrush, QTextOption

from utils.logger import logger
from core.enums import ZplFont, TextAlignment, AnchorPosition
from core.utils.conversions import (
    dots_to_points,
    mm_to_dots,
    dots_to_mm,
)
from .base import BaseElement, ElementConfig


@dataclass
class TextConfig(ElementConfig):
    """Конфігурація текстового елементу"""

    font_code: str = ZplFont.SCALABLE.code
    font_display_name: str = ZplFont.SCALABLE.display_name
    font_height_dots: int = 40
    font_width_dots: int = 40
    font_multiplier: int = 1
    alignment: str = TextAlignment.LEFT.key
    block_width_mm: float = 0.0
    anchor_position: int = AnchorPosition.TOP_LEFT.value
    keep_aspect_ratio: bool = False
    box_width_mm: float = 0.0
    box_height_mm: float = 0.0

class TextElement(BaseElement):
    """Текстовий елемент"""

    def __init__(self, config: ElementConfig, text: str = "Text", font_size: int = 20):
        created_config = not isinstance(config, TextConfig)
        text_config = config if isinstance(config, TextConfig) else TextConfig(
            x=config.x,
            y=config.y,
            rotation=getattr(config, 'rotation', 0),
        )
        super().__init__(text_config)
        self.config: TextConfig = text_config
        self.text = text
        self.font_size = font_size
        self.data_field: Optional[str] = None

        # Font styles
        self.bold = False
        self.italic = False  # ZPL не підтримує italic без custom font
        self.underline = False

        # Синхронізація назв шрифту
        font_enum = ZplFont.by_code(self.config.font_code)
        self.config.font_display_name = font_enum.display_name

        if not font_enum.scalable:
            if self.config.font_multiplier <= 0:
                self.config.font_multiplier = 1
            self.config.font_height_dots = font_enum.base_height * self.config.font_multiplier
            self.config.font_width_dots = font_enum.base_width * self.config.font_multiplier
        else:
            if created_config or self.config.font_height_dots <= 0:
                self.config.font_height_dots = font_size
            if created_config or self.config.font_width_dots <= 0:
                self.config.font_width_dots = self.config.font_height_dots

        # Оновити font_size щоб співпадав з height у dots
        self.font_size = self.config.font_height_dots

    def to_dict(self):
        """Серіалізація у JSON"""
        return {
            'type': 'text',
            'x': self.config.x,
            'y': self.config.y,
            'text': self.text,
            'font_size': self.font_size,
            'data_field': self.data_field,
            'bold': self.bold,
            'italic': self.italic,
            'underline': self.underline,
            'font': {
                'code': self.config.font_code,
                'display_name': self.config.font_display_name,
                'height_dots': self.config.font_height_dots,
                'width_dots': self.config.font_width_dots,
                'multiplier': self.config.font_multiplier,
            },
            'alignment': self.config.alignment,
            'block_width_mm': self.config.block_width_mm,
            'anchor_position': self.config.anchor_position,
            'keep_aspect_ratio': self.config.keep_aspect_ratio,
            'box_width_mm': self.config.box_width_mm,
            'box_height_mm': self.config.box_height_mm,
        }

    @classmethod
    def from_dict(cls, data):
        font_data = data.get('font', {})
        font_code = font_data.get('code', '0')
        font_enum = ZplFont.by_code(font_code)
        multiplier = font_data.get('multiplier', 1)
        font_height = font_data.get('height_dots', data.get('font_size', 20))
        font_width = font_data.get('width_dots', font_height)

        config = TextConfig(
            x=data['x'],
            y=data['y'],
            rotation=data.get('rotation', 0),
            font_code=font_code,
            font_display_name=font_data.get('display_name', font_enum.display_name),
            font_height_dots=font_height,
            font_width_dots=font_width,
            font_multiplier=multiplier,
            alignment=data.get('alignment', TextAlignment.LEFT.key),
            block_width_mm=data.get('block_width_mm', 0.0),
            anchor_position=data.get('anchor_position', AnchorPosition.TOP_LEFT.value),
            keep_aspect_ratio=data.get('keep_aspect_ratio', False),
            box_width_mm=data.get('box_width_mm', 0.0),
            box_height_mm=data.get('box_height_mm', 0.0),
        )

        element = cls(config, data.get('text', 'Text'), data.get('font_size', font_height))
        element.data_field = data.get('data_field')
        element.bold = data.get('bold', False)
        element.italic = data.get('italic', False)
        element.underline = data.get('underline', False)

        logger.debug(
            f"[TEXT-FONT] Loaded element: font={config.font_code}, height={config.font_height_dots}, "
            f"width={config.font_width_dots}, multiplier={config.font_multiplier}"
        )

        return element

    def to_zpl(self, dpi: int) -> str:
        """Генерація ZPL коду"""

        x_dots = mm_to_dots(self.config.x, dpi)
        y_dots = mm_to_dots(self.config.y, dpi)
        content = self.data_field if self.data_field else self.text

        font_enum = ZplFont.by_code(self.config.font_code)
        multiplier = max(self.config.font_multiplier, 1)
        height_dots = self.config.font_height_dots
        width_dots = self.config.font_width_dots

        if not font_enum.scalable:
            height_dots = font_enum.base_height * multiplier
            width_dots = font_enum.base_width * multiplier
        else:
            if height_dots <= 0:
                height_dots = self.font_size
            if width_dots <= 0:
                width_dots = height_dots
            if self.bold:
                width_dots = int(height_dots * 1.5)

        lines = [f"^FO{x_dots},{y_dots}"]
        lines.append(f"^A{font_enum.code}N,{height_dots},{width_dots}")
        logger.debug(f"[ZPL-TEXT-FONT] ^A{font_enum.code}N,{height_dots},{width_dots}")

        alignment = TextAlignment.from_key(self.config.alignment)
        block_width_mm = self.config.block_width_mm or self.config.box_width_mm
        if alignment != TextAlignment.LEFT or self.config.block_width_mm > 0:
            block_width_dots = mm_to_dots(block_width_mm, dpi) if block_width_mm else width_dots
            block_width_dots = max(block_width_dots, width_dots)
            lines.append(f"^FB{block_width_dots},1,0,{alignment.zpl_code},0")
            logger.debug(f"[ZPL-TEXT-ALIGN] ^FB{block_width_dots},1,0,{alignment.zpl_code},0")

        lines.append(f"^FD{content}^FS")

        if self.underline:
            underline_y = y_dots + height_dots + 2
            underline_width = max(width_dots * max(len(content), 1), width_dots)
            lines.append(f"^FO{x_dots},{underline_y}^GB{underline_width},1,1^FS")
            logger.debug(f"[ZPL-UNDERLINE] y={underline_y}, width={underline_width}")

        logger.debug(
            f"[ZPL-FONT-STYLES] Bold={self.bold}, Italic={self.italic}, Underline={self.underline}"
        )

        return '\n'.join(lines)


class GraphicsTextItem(QGraphicsTextItem):
    """Графічний текстовий елемент з розширеними можливостями"""

    position_changed = Signal(float, float)
    size_changed = Signal(float, float)

    HANDLE_TOP_LEFT = 0
    HANDLE_TOP_MIDDLE = 1
    HANDLE_TOP_RIGHT = 2
    HANDLE_MIDDLE_LEFT = 3
    HANDLE_MIDDLE_RIGHT = 4
    HANDLE_BOTTOM_LEFT = 5
    HANDLE_BOTTOM_MIDDLE = 6
    HANDLE_BOTTOM_RIGHT = 7

    handleSize = 8.0

    def __init__(self, element: TextElement, dpi: int = 203, canvas=None):
        super().__init__(element.text)
        self.element = element
        self.dpi = dpi
        self.canvas = canvas

        self.handles = {}
        self.handleSelected = None
        self._initial_rect = QRectF()
        self._initial_font_point = 0.0
        self._initial_text_width = 0.0
        self._aspect_ratio = 1.0

        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self.snap_enabled = True
        self.grid_step_mm = 1.0
        self.snap_threshold_mm = 1.0

        self.update_display_text()
        self.update_display()
        self._apply_alignment()
        self._apply_box_dimensions()
        self.set_anchor_point(AnchorPosition(self.element.config.anchor_position))

        x_px = self._mm_to_px(self.element.config.x)
        y_px = self._mm_to_px(self.element.config.y)
        self.setPos(x_px, y_px)

        self.document().contentsChanged.connect(self._on_document_changed)
        self._on_document_changed()
        self.updateHandlesPos()
    
    def _mm_to_px(self, mm: float) -> float:
        return mm * self.dpi / 25.4

    def _px_to_mm(self, px: float) -> float:
        return px * 25.4 / self.dpi

    def update_display_text(self):
        display = self.element.data_field if self.element.data_field else self.element.text
        self.setPlainText(display)

    def update_display(self):
        self._setup_font()
        self._apply_alignment()
        self._apply_box_dimensions()
        logger.debug(
            f"[TEXT-ITEM] Display updated: font={self.element.config.font_code}, "
            f"height={self.element.config.font_height_dots}, width={self.element.config.font_width_dots}"
        )
        self.updateHandlesPos()
        self.update()

    def _setup_font(self):
        font_enum = ZplFont.by_code(self.element.config.font_code)
        if font_enum.scalable:
            height_dots = max(self.element.config.font_height_dots, 1)
            width_dots = max(self.element.config.font_width_dots, height_dots)
        else:
            multiplier = max(self.element.config.font_multiplier, 1)
            height_dots = font_enum.base_height * multiplier
            width_dots = font_enum.base_width * multiplier
            self.element.config.font_height_dots = height_dots
            self.element.config.font_width_dots = width_dots

        point_size = max(dots_to_points(height_dots, self.dpi), 1.0)
        font = QFont(self.font())
        font.setPointSizeF(point_size)
        font.setBold(self.element.bold)
        font.setUnderline(self.element.underline)
        self.setFont(font)
        self.element.font_size = int(round(height_dots))

    def _apply_alignment(self):
        alignment = TextAlignment.from_key(self.element.config.alignment)
        option = QTextOption(self.document().defaultTextOption())
        qt_alignment = {
            TextAlignment.LEFT: Qt.AlignLeft,
            TextAlignment.CENTER: Qt.AlignHCenter,
            TextAlignment.RIGHT: Qt.AlignRight,
            TextAlignment.JUSTIFIED: Qt.AlignJustify,
        }[alignment]
        option.setAlignment(qt_alignment)
        self.document().setDefaultTextOption(option)

    def _apply_box_dimensions(self):
        width_mm = 0.0
        if self.element.config.box_width_mm > 0:
            width_mm = self.element.config.box_width_mm
        elif self.element.config.block_width_mm > 0:
            width_mm = self.element.config.block_width_mm

        if width_mm > 0:
            self.document().setTextWidth(self._mm_to_px(width_mm))
        else:
            self.document().setTextWidth(-1)

    def _on_document_changed(self):
        self.prepareGeometryChange()
        self.updateHandlesPos()
        bounds = self.boundingRect()
        width_mm = self._px_to_mm(bounds.width())
        height_mm = self._px_to_mm(bounds.height())
        if self.element.config.box_width_mm <= 0:
            self.element.config.box_width_mm = width_mm
        if self.element.config.box_height_mm <= 0:
            self.element.config.box_height_mm = height_mm

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            x_mm = self._px_to_mm(new_pos.x())
            y_mm = self._px_to_mm(new_pos.y())

            if self.canvas:
                self.canvas.cursor_position_changed.emit(x_mm, y_mm)

            if self.snap_enabled:
                snapped_x = self._snap_to_grid(x_mm, 'x')
                snapped_y = self._snap_to_grid(y_mm, 'y')
                return QPointF(self._mm_to_px(snapped_x), self._mm_to_px(snapped_y))

            return new_pos

        if change == QGraphicsTextItem.ItemPositionHasChanged:
            x_mm = self._px_to_mm(self.pos().x())
            y_mm = self._px_to_mm(self.pos().y())

            if self.snap_enabled:
                x_mm = self._snap_to_grid(x_mm)
                y_mm = self._snap_to_grid(y_mm)

            self.element.config.x = x_mm
            self.element.config.y = y_mm
            self.position_changed.emit(x_mm, y_mm)

            if (
                self.canvas
                and getattr(self.canvas, 'bounds_update_callback', None)
                and self.isSelected()
            ):
                self.canvas.bounds_update_callback(self)

        return super().itemChange(change, value)

    def _snap_to_grid(self, value_mm, axis='x'):
        from config import SnapMode

        if not self.canvas:
            size = 1.0
            offset = 0.0
            threshold = 1.0
        else:
            config = self.canvas.grid_config
            if config.snap_mode != SnapMode.GRID:
                return value_mm
            size = config.size_x_mm if axis == 'x' else config.size_y_mm
            offset = config.offset_x_mm if axis == 'x' else config.offset_y_mm
            threshold = size / 2

        relative = value_mm - offset
        rounded = round(relative / size) * size + offset
        if abs(value_mm - rounded) <= threshold:
            return rounded
        return value_mm

    def update_text(self, text: str):
        self.element.text = text
        self.update_display_text()
        self.updateHandlesPos()

    def update_font_size(self, font_size: int):
        self.element.font_size = font_size
        self.element.config.font_height_dots = font_size
        if ZplFont.by_code(self.element.config.font_code).scalable:
            self.element.config.font_width_dots = max(
                self.element.config.font_width_dots, font_size
            )
        self.update_display()
        self.updateHandlesPos()
        self.size_changed.emit(
            self.element.config.box_width_mm,
            self.element.config.box_height_mm,
        )

    def set_font(self, font: ZplFont, multiplier: int = 1):
        self.element.config.font_code = font.code
        self.element.config.font_display_name = font.display_name
        self.element.config.font_multiplier = max(multiplier, 1)
        if font.scalable:
            if self.element.config.font_height_dots <= 0:
                self.element.config.font_height_dots = self.element.font_size
            if self.element.config.font_width_dots <= 0:
                self.element.config.font_width_dots = self.element.config.font_height_dots
        else:
            self.element.config.font_height_dots = font.base_height * self.element.config.font_multiplier
            self.element.config.font_width_dots = font.base_width * self.element.config.font_multiplier
        self.update_display()
        self.updateHandlesPos()
        self.size_changed.emit(
            self.element.config.box_width_mm,
            self.element.config.box_height_mm,
        )

    def set_alignment(self, alignment: TextAlignment):
        self.element.config.alignment = alignment.key
        self._apply_alignment()
        self.update()

    def set_block_width_mm(self, width_mm: float):
        self.element.config.block_width_mm = max(width_mm, 0.0)
        self._apply_box_dimensions()
        self.updateHandlesPos()

    def set_keep_aspect_ratio(self, enabled: bool):
        self.element.config.keep_aspect_ratio = enabled

    def set_box_size(self, width_mm: float = None, height_mm: float = None):
        if width_mm is not None:
            self.element.config.box_width_mm = max(width_mm, 0.0)
        if height_mm is not None:
            self.element.config.box_height_mm = max(height_mm, 0.0)
        self._apply_box_dimensions()
        self.updateHandlesPos()
        self.update()
        self.size_changed.emit(
            self.element.config.box_width_mm,
            self.element.config.box_height_mm,
        )

    def updateHandlesPos(self):
        rect = self.boundingRect()
        s = self.handleSize
        self.handles = {
            self.HANDLE_TOP_LEFT: QRectF(rect.left(), rect.top(), s, s),
            self.HANDLE_TOP_MIDDLE: QRectF(rect.center().x() - s / 2, rect.top(), s, s),
            self.HANDLE_TOP_RIGHT: QRectF(rect.right() - s, rect.top(), s, s),
            self.HANDLE_MIDDLE_LEFT: QRectF(rect.left(), rect.center().y() - s / 2, s, s),
            self.HANDLE_MIDDLE_RIGHT: QRectF(rect.right() - s, rect.center().y() - s / 2, s, s),
            self.HANDLE_BOTTOM_LEFT: QRectF(rect.left(), rect.bottom() - s, s, s),
            self.HANDLE_BOTTOM_MIDDLE: QRectF(rect.center().x() - s / 2, rect.bottom() - s, s, s),
            self.HANDLE_BOTTOM_RIGHT: QRectF(rect.right() - s, rect.bottom() - s, s, s),
        }

    def handleAt(self, point: QPointF):
        for handle_id, rect in self.handles.items():
            if rect.contains(point):
                return handle_id
        return None

    def hoverMoveEvent(self, event):
        if self.isSelected():
            handle = self.handleAt(event.pos())
            cursors = {
                self.HANDLE_TOP_LEFT: Qt.SizeFDiagCursor,
                self.HANDLE_TOP_MIDDLE: Qt.SizeVerCursor,
                self.HANDLE_TOP_RIGHT: Qt.SizeBDiagCursor,
                self.HANDLE_MIDDLE_LEFT: Qt.SizeHorCursor,
                self.HANDLE_MIDDLE_RIGHT: Qt.SizeHorCursor,
                self.HANDLE_BOTTOM_LEFT: Qt.SizeBDiagCursor,
                self.HANDLE_BOTTOM_MIDDLE: Qt.SizeVerCursor,
                self.HANDLE_BOTTOM_RIGHT: Qt.SizeFDiagCursor,
            }
            self.setCursor(cursors.get(handle, Qt.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self.handleSelected = self.handleAt(event.pos())
        self._initial_rect = self.boundingRect()
        self._initial_font_point = self.font().pointSizeF() or float(self.font().pointSize())
        self._initial_text_width = self.document().textWidth() if self.document().textWidth() > 0 else self._initial_rect.width()
        self._aspect_ratio = (
            self._initial_rect.width() / self._initial_rect.height()
            if self._initial_rect.height() > 0
            else 1.0
        )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handleSelected is not None:
            self.interactiveResize(event.pos())
        else:
            super().mouseMoveEvent(event)

    def interactiveResize(self, mousePos: QPointF):
        if self.handleSelected != self.HANDLE_BOTTOM_RIGHT:
            return

        new_width = max(mousePos.x(), self.handleSize * 2)
        new_height = max(mousePos.y(), self.handleSize * 2)

        if self.element.config.keep_aspect_ratio and self._aspect_ratio > 0:
            new_height = new_width / self._aspect_ratio

        self.prepareGeometryChange()
        self.document().setTextWidth(new_width)

        if self._initial_rect.height() > 0:
            scale = new_height / self._initial_rect.height()
            new_point = max(self._initial_font_point * scale, 1.0)
            font = self.font()
            font.setPointSizeF(new_point)
            self.setFont(font)
            height_mm = self._px_to_mm(new_height)
            width_mm = self._px_to_mm(new_width)
            self.element.config.font_height_dots = max(mm_to_dots(height_mm, self.dpi), 1)
            self.element.config.font_width_dots = max(mm_to_dots(width_mm, self.dpi), 1)
            self.element.font_size = self.element.config.font_height_dots

        width_mm = self._px_to_mm(new_width)
        height_mm = self._px_to_mm(new_height)
        self.element.config.box_width_mm = width_mm
        self.element.config.box_height_mm = height_mm
        self.size_changed.emit(width_mm, height_mm)
        self.updateHandlesPos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.handleSelected = None
        self.updateHandlesPos()
        super().mouseReleaseEvent(event)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setBrush(QBrush(QColor(220, 20, 60)))
            painter.setPen(Qt.NoPen)
            for rect in self.handles.values():
                painter.drawRect(rect)

            anchor_point = self.transformOriginPoint()
            painter.setPen(QPen(QColor(220, 20, 60), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(anchor_point, 5, 5)
            painter.drawLine(anchor_point.x() - 8, anchor_point.y(), anchor_point.x() + 8, anchor_point.y())
            painter.drawLine(anchor_point.x(), anchor_point.y() - 8, anchor_point.x(), anchor_point.y() + 8)

    def set_anchor_point(self, anchor: AnchorPosition):
        rect = self.boundingRect()
        origins = {
            AnchorPosition.TOP_LEFT: rect.topLeft(),
            AnchorPosition.TOP_CENTER: QPointF(rect.center().x(), rect.top()),
            AnchorPosition.TOP_RIGHT: rect.topRight(),
            AnchorPosition.CENTER_LEFT: QPointF(rect.left(), rect.center().y()),
            AnchorPosition.CENTER: rect.center(),
            AnchorPosition.CENTER_RIGHT: QPointF(rect.right(), rect.center().y()),
            AnchorPosition.BOTTOM_LEFT: rect.bottomLeft(),
            AnchorPosition.BOTTOM_CENTER: QPointF(rect.center().x(), rect.bottom()),
            AnchorPosition.BOTTOM_RIGHT: rect.bottomRight(),
        }
        self.setTransformOriginPoint(origins[anchor])
        self.element.config.anchor_position = anchor.value

    def change_anchor(self, anchor: AnchorPosition):
        old_point = self.mapToScene(self.transformOriginPoint())
        self.set_anchor_point(anchor)
        new_point = self.mapToScene(self.transformOriginPoint())
        offset = old_point - new_point
        self.setPos(self.pos() + offset)
