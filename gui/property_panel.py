# -*- coding: utf-8 -*-
"""Панель свойств элемента"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QPushButton,
)
from PySide6.QtCore import Signal
from utils.logger import logger
from utils.unit_converter import UnitConverter
from config import UNIT_DECIMALS, UNIT_STEPS
from gui.widgets.font_selector import FontSelector
from gui.widgets.alignment_selector import AlignmentSelector
from gui.widgets.anchor_selector import AnchorSelector
from core.enums import ZplFont, TextAlignment, AnchorPosition
from core.elements.text_element import TextElement

class PropertyPanel(QWidget):
    """Панель свойств выбранного элемента"""
    
    property_changed = Signal(str, object)  # (property_name, new_value)
    
    def __init__(self):
        super().__init__()
        self.current_element = None
        self.current_graphics_item = None
        self._setup_ui()
        logger.info("PropertyPanel initialized")
    
    def _setup_ui(self):
        """Создать UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # === Position Group ===
        pos_group = QGroupBox("Position")
        pos_form = QFormLayout()
        
        self.x_input = QDoubleSpinBox()
        self.x_input.setRange(0, 100)
        self.x_input.setDecimals(1)
        self.x_input.setSingleStep(0.1)
        self.x_input.setSuffix(" mm")
        self.x_input.valueChanged.connect(
            lambda v: self._on_property_change('x', v)
        )
        pos_form.addRow("X:", self.x_input)
        
        self.y_input = QDoubleSpinBox()
        self.y_input.setRange(0, 100)
        self.y_input.setDecimals(1)
        self.y_input.setSingleStep(0.1)
        self.y_input.setSuffix(" mm")
        self.y_input.valueChanged.connect(
            lambda v: self._on_property_change('y', v)
        )
        pos_form.addRow("Y:", self.y_input)
        
        pos_group.setLayout(pos_form)
        
        # === Text Properties Group ===
        text_group = QGroupBox("Text Properties")
        text_form = QFormLayout()
        
        self.text_input = QLineEdit()
        self.text_input.textChanged.connect(
            lambda v: self._on_property_change('text', v)
        )
        text_form.addRow("Text:", self.text_input)

        self.font_selector = FontSelector()
        self.font_selector.fontChanged.connect(self._on_font_selected)
        text_form.addRow("Font:", self.font_selector)

        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(10, 600)
        self.font_size_input.setSuffix(" dots")
        self.font_size_input.valueChanged.connect(self._on_font_height_changed)
        text_form.addRow("Font Height:", self.font_size_input)

        self.font_width_input = QSpinBox()
        self.font_width_input.setRange(10, 600)
        self.font_width_input.setSuffix(" dots")
        self.font_width_input.valueChanged.connect(self._on_font_width_changed)
        text_form.addRow("Font Width:", self.font_width_input)

        self.font_multiplier_input = QSpinBox()
        self.font_multiplier_input.setRange(1, 10)
        self.font_multiplier_input.valueChanged.connect(self._on_font_multiplier_changed)
        text_form.addRow("Multiplier:", self.font_multiplier_input)
        self.font_multiplier_input.setVisible(False)
        
        self.placeholder_input = QLineEdit()
        self.placeholder_input.setPlaceholderText("{{FIELD_NAME}}")
        self.placeholder_input.textChanged.connect(
            lambda v: self._on_property_change('data_field', v if v else None)
        )
        text_form.addRow("Placeholder:", self.placeholder_input)

        self.alignment_selector = AlignmentSelector()
        self.alignment_selector.alignmentChanged.connect(self._on_alignment_changed)
        text_form.addRow("Alignment:", self.alignment_selector)

        self.block_width_input = QDoubleSpinBox()
        self.block_width_input.setRange(0, 500)
        self.block_width_input.setDecimals(1)
        self.block_width_input.setSingleStep(1.0)
        self.block_width_input.setSuffix(" mm")
        self.block_width_input.valueChanged.connect(self._on_block_width_changed)
        text_form.addRow("Block Width:", self.block_width_input)

        self.text_width_input = QDoubleSpinBox()
        self.text_width_input.setRange(1, 500)
        self.text_width_input.setDecimals(1)
        self.text_width_input.setSingleStep(0.5)
        self.text_width_input.setSuffix(" mm")
        self.text_width_input.valueChanged.connect(lambda v: self._on_text_box_changed('width', v))
        text_form.addRow("Box Width:", self.text_width_input)

        self.text_height_input = QDoubleSpinBox()
        self.text_height_input.setRange(1, 500)
        self.text_height_input.setDecimals(1)
        self.text_height_input.setSingleStep(0.5)
        self.text_height_input.setSuffix(" mm")
        self.text_height_input.valueChanged.connect(lambda v: self._on_text_box_changed('height', v))
        text_form.addRow("Box Height:", self.text_height_input)

        styles_label = QLabel("Styles:")
        text_form.addRow(styles_label)

        self.bold_checkbox = QCheckBox("Bold (Ctrl+B)")
        self.bold_checkbox.stateChanged.connect(self._on_bold_changed)
        text_form.addRow("", self.bold_checkbox)

        self.italic_checkbox = QCheckBox("Italic [Requires font upload to printer]")
        self.italic_checkbox.setEnabled(False)
        self.italic_checkbox.setToolTip("ZPL does not support italic without uploading italic font to printer")
        text_form.addRow("", self.italic_checkbox)

        self.underline_checkbox = QCheckBox("Underline (Ctrl+U)")
        self.underline_checkbox.stateChanged.connect(self._on_underline_changed)
        text_form.addRow("", self.underline_checkbox)

        self.keep_aspect_ratio_check = QCheckBox("Keep aspect ratio")
        self.keep_aspect_ratio_check.stateChanged.connect(self._on_keep_aspect_ratio_changed)
        text_form.addRow("", self.keep_aspect_ratio_check)

        self.anchor_selector = AnchorSelector()
        self.anchor_selector.anchorChanged.connect(self._on_anchor_changed)
        text_form.addRow("Anchor:", self.anchor_selector)
        
        text_group.setLayout(text_form)
        self.text_group = text_group
        
        # === Barcode Properties Group ===
        barcode_group = QGroupBox("Barcode Properties")
        barcode_form = QFormLayout()
        
        self.barcode_type_label = QLabel()
        barcode_form.addRow("Type:", self.barcode_type_label)
        
        self.barcode_data_input = QLineEdit()
        self.barcode_data_input.textChanged.connect(
            lambda v: self._on_property_change('barcode_data', v)
        )
        barcode_form.addRow("Data:", self.barcode_data_input)
        
        self.barcode_width_input = QSpinBox()
        self.barcode_width_input.setRange(20, 100)
        self.barcode_width_input.setSuffix(" mm")
        self.barcode_width_input.valueChanged.connect(
            lambda v: self._on_property_change('barcode_width', v)
        )
        barcode_form.addRow("Width:", self.barcode_width_input)
        
        self.barcode_height_input = QSpinBox()
        self.barcode_height_input.setRange(10, 100)
        self.barcode_height_input.setSuffix(" mm")
        self.barcode_height_input.valueChanged.connect(
            lambda v: self._on_property_change('barcode_height', v)
        )
        barcode_form.addRow("Height:", self.barcode_height_input)
        
        self.barcode_placeholder_input = QLineEdit()
        self.barcode_placeholder_input.setPlaceholderText("{{FIELD_NAME}}")
        self.barcode_placeholder_input.textChanged.connect(
            lambda v: self._on_property_change('barcode_data_field', v if v else None)
        )
        barcode_form.addRow("Placeholder:", self.barcode_placeholder_input)
        
        barcode_group.setLayout(barcode_form)
        barcode_group.setVisible(False)
        self.barcode_group = barcode_group
        
        # === Shape Properties Group ===
        shape_group = QGroupBox("Shape Properties")
        shape_form = QFormLayout()
        
        self.shape_type_label = QLabel()
        shape_form.addRow("Type:", self.shape_type_label)
        
        self.shape_width_input = QDoubleSpinBox()
        self.shape_width_input.setRange(1, 100)
        self.shape_width_input.setDecimals(1)
        self.shape_width_input.setSingleStep(0.5)
        self.shape_width_input.setSuffix(" mm")
        self.shape_width_input.valueChanged.connect(
            lambda v: self._on_property_change('shape_width', v)
        )
        shape_form.addRow("Width:", self.shape_width_input)
        
        self.shape_height_input = QDoubleSpinBox()
        self.shape_height_input.setRange(1, 100)
        self.shape_height_input.setDecimals(1)
        self.shape_height_input.setSingleStep(0.5)
        self.shape_height_input.setSuffix(" mm")
        self.shape_height_input.valueChanged.connect(
            lambda v: self._on_property_change('shape_height', v)
        )
        shape_form.addRow("Height:", self.shape_height_input)
        
        self.shape_fill_input = QCheckBox()
        self.shape_fill_input.stateChanged.connect(
            lambda v: self._on_property_change('shape_fill', v == 2)
        )
        shape_form.addRow("Fill:", self.shape_fill_input)
        
        self.shape_thickness_input = QDoubleSpinBox()
        self.shape_thickness_input.setRange(0.5, 10)
        self.shape_thickness_input.setDecimals(1)
        self.shape_thickness_input.setSingleStep(0.5)
        self.shape_thickness_input.setSuffix(" mm")
        self.shape_thickness_input.valueChanged.connect(
            lambda v: self._on_property_change('shape_thickness', v)
        )
        shape_form.addRow("Thickness:", self.shape_thickness_input)
        
        shape_group.setLayout(shape_form)
        shape_group.setVisible(False)
        self.shape_group = shape_group
        
        # === IMAGE PROPERTIES ===
        image_group = QGroupBox("Image Properties")
        image_layout = QFormLayout()
        
        # Width
        self.image_width_input = QDoubleSpinBox()
        self.image_width_input.setRange(1, 200)
        self.image_width_input.setDecimals(1)
        self.image_width_input.setSingleStep(1.0)
        self.image_width_input.setSuffix(" mm")
        self.image_width_input.valueChanged.connect(self._on_image_width_changed)
        image_layout.addRow("Width:", self.image_width_input)
        
        # Height
        self.image_height_input = QDoubleSpinBox()
        self.image_height_input.setRange(1, 200)
        self.image_height_input.setDecimals(1)
        self.image_height_input.setSingleStep(1.0)
        self.image_height_input.setSuffix(" mm")
        self.image_height_input.valueChanged.connect(self._on_image_height_changed)
        image_layout.addRow("Height:", self.image_height_input)
        
        # Change Image button
        self.change_image_btn = QPushButton("Change Image...")
        self.change_image_btn.clicked.connect(self._on_change_image)
        image_layout.addRow("", self.change_image_btn)
        
        image_group.setLayout(image_layout)
        image_group.setVisible(False)
        self.image_group = image_group
        
        # Собрать layout
        layout.addWidget(pos_group)
        layout.addWidget(text_group)
        layout.addWidget(barcode_group)
        layout.addWidget(shape_group)
        layout.addWidget(image_group)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setMinimumWidth(250)
        
        # Изначально заблокировать
        self.setEnabled(False)
    
    def set_element(self, element, graphics_item):
        """Отобразить свойства элемента"""
        self.current_element = element
        self.current_graphics_item = graphics_item
        
        # Подключить position_changed сигнал
        if graphics_item and hasattr(graphics_item, 'position_changed'):
            try:
                graphics_item.position_changed.disconnect()
            except:
                pass
            graphics_item.position_changed.connect(self.update_position)

        if graphics_item and hasattr(graphics_item, 'size_changed'):
            try:
                graphics_item.size_changed.disconnect()
            except:
                pass
            graphics_item.size_changed.connect(self._on_text_size_changed)
        
        if element:
            self.setEnabled(True)
            logger.debug(f"Property panel activated for element at ({element.config.x}, {element.config.y})")
            
            # Отримати current unit з MainWindow
            main_window = self._get_main_window()
            if not main_window:
                return
            
            current_unit = main_window.current_unit
            decimals = UNIT_DECIMALS[current_unit]
            step = UNIT_STEPS[current_unit]
            
            # Заблокировать сигналы чтобы не вызвать изменения
            self.blockSignals(True)
            
            # Конвертувати значення з MM в current unit
            x_display = UnitConverter.mm_to_unit(element.config.x, current_unit)
            y_display = UnitConverter.mm_to_unit(element.config.y, current_unit)
            
            # Оновити Position group
            self.x_input.blockSignals(True)
            self.x_input.setDecimals(decimals)
            self.x_input.setSingleStep(step)
            self.x_input.setSuffix(f" {current_unit.value}")
            self.x_input.setValue(x_display)
            self.x_input.blockSignals(False)
            
            self.y_input.blockSignals(True)
            self.y_input.setDecimals(decimals)
            self.y_input.setSingleStep(step)
            self.y_input.setSuffix(f" {current_unit.value}")
            self.y_input.setValue(y_display)
            self.y_input.blockSignals(False)
            
            # Определить тип элемента
            from core.elements.barcode_element import BarcodeElement
            from core.elements.shape_element import RectangleElement, CircleElement, LineElement
            
            if isinstance(element, TextElement):
                self.text_group.setVisible(True)
                self.barcode_group.setVisible(False)
                self.shape_group.setVisible(False)

                self.text_input.setText(element.text)
                self.placeholder_input.setText(
                    element.data_field if element.data_field else ""
                )

                font_enum = ZplFont.by_code(element.config.font_code)
                self.font_selector.blockSignals(True)
                self.font_selector.set_font(font_enum)
                self.font_selector.blockSignals(False)

                self.font_size_input.blockSignals(True)
                self.font_size_input.setValue(element.config.font_height_dots)
                self.font_size_input.blockSignals(False)

                if font_enum.scalable:
                    self.font_width_input.setVisible(True)
                    self.font_width_input.blockSignals(True)
                    self.font_width_input.setValue(element.config.font_width_dots)
                    self.font_width_input.blockSignals(False)
                    self.font_multiplier_input.setVisible(False)
                else:
                    self.font_width_input.setVisible(False)
                    self.font_multiplier_input.setVisible(True)
                    self.font_multiplier_input.blockSignals(True)
                    self.font_multiplier_input.setValue(element.config.font_multiplier)
                    self.font_multiplier_input.blockSignals(False)

                self.bold_checkbox.setChecked(element.bold)
                self.underline_checkbox.setChecked(element.underline)
                logger.debug(f"[PROP-PANEL] Loaded styles: Bold={element.bold}, Underline={element.underline}")

                self.alignment_selector.blockSignals(True)
                self.alignment_selector.set_alignment(TextAlignment.from_key(element.config.alignment))
                self.alignment_selector.blockSignals(False)

                self.block_width_input.blockSignals(True)
                self.block_width_input.setValue(element.config.block_width_mm)
                self.block_width_input.blockSignals(False)

                if graphics_item:
                    width_mm = element.config.box_width_mm or graphics_item._px_to_mm(graphics_item.boundingRect().width())
                    height_mm = element.config.box_height_mm or graphics_item._px_to_mm(graphics_item.boundingRect().height())
                else:
                    width_mm = element.config.box_width_mm or 10.0
                    height_mm = element.config.box_height_mm or 5.0

                self.text_width_input.blockSignals(True)
                self.text_width_input.setValue(max(width_mm, 1.0))
                self.text_width_input.blockSignals(False)

                self.text_height_input.blockSignals(True)
                self.text_height_input.setValue(max(height_mm, 1.0))
                self.text_height_input.blockSignals(False)

                self.keep_aspect_ratio_check.blockSignals(True)
                self.keep_aspect_ratio_check.setChecked(element.config.keep_aspect_ratio)
                self.keep_aspect_ratio_check.blockSignals(False)

                self.anchor_selector.blockSignals(True)
                self.anchor_selector.set_anchor(AnchorPosition(element.config.anchor_position))
                self.anchor_selector.blockSignals(False)

            elif isinstance(element, BarcodeElement):
                # Показать только Barcode Properties
                self.text_group.setVisible(False)
                self.barcode_group.setVisible(True)
                self.shape_group.setVisible(False)
                
                self.barcode_type_label.setText(element.barcode_type)
                self.barcode_data_input.setText(element.data)
                self.barcode_width_input.setValue(int(element.width))
                self.barcode_height_input.setValue(int(element.height))
                self.barcode_placeholder_input.setText(
                    element.data_field if element.data_field else ""
                )
            
            elif hasattr(element.config, 'image_path'):
                # Image element
                self.text_group.setVisible(False)
                self.barcode_group.setVisible(False)
                self.shape_group.setVisible(False)
                self.image_group.setVisible(True)
                
                # Заповнити поля
                self.image_width_input.blockSignals(True)
                self.image_height_input.blockSignals(True)
                
                self.image_width_input.setValue(element.config.width)
                self.image_height_input.setValue(element.config.height)
                
                self.image_width_input.blockSignals(False)
                self.image_height_input.blockSignals(False)
                
                logger.debug(f"[PROP-IMAGE] Set properties: {element.config.width}x{element.config.height}mm")
            
            elif isinstance(element, (RectangleElement, CircleElement)):
                # Показать только Shape Properties
                self.text_group.setVisible(False)
                self.barcode_group.setVisible(False)
                self.shape_group.setVisible(True)
                
                shape_type = "Rectangle" if isinstance(element, RectangleElement) else "Circle"
                self.shape_type_label.setText(shape_type)
                self.shape_width_input.setValue(element.config.width)
                self.shape_height_input.setValue(element.config.height)
                self.shape_fill_input.setChecked(element.config.fill)
                self.shape_thickness_input.setValue(element.config.border_thickness)
            
            elif isinstance(element, LineElement):
                # Line немає width/height, тільки thickness
                # Показати Shape Properties без width/height
                self.text_group.setVisible(False)
                self.barcode_group.setVisible(False)
                self.shape_group.setVisible(True)
                
                self.shape_type_label.setText("Line")
                self.shape_width_input.setVisible(False)
                self.shape_height_input.setVisible(False)
                self.shape_fill_input.setVisible(False)
                self.shape_thickness_input.setValue(element.config.thickness)
            else:
                # Відновити width/height якщо були приховані
                self.shape_width_input.setVisible(True)
                self.shape_height_input.setVisible(True)
                self.shape_fill_input.setVisible(True)
            
            self.blockSignals(False)
        else:
            self.setEnabled(False)
            logger.debug("Property panel deactivated")
    
    def _on_property_change(self, prop_name, value):
        """Обработка изменения свойства"""
        if not self.current_element:
            return
        
        main_window = self._get_main_window()
        if not main_window:
            return
        
        current_unit = main_window.current_unit
        
        # Обновить элемент
        if prop_name == 'x':
            # Конвертувати назад в MM перед збереженням
            x_mm = UnitConverter.unit_to_mm(value, current_unit)
            self.current_element.config.x = x_mm
            
            logger.debug(f"[PROP-PANEL] X changed: {value:.2f}{current_unit.value} = {x_mm:.2f}mm")
            
            if self.current_graphics_item:
                x_px = int(x_mm * self.current_graphics_item.dpi / 25.4)
                self.current_graphics_item.setPos(
                    x_px, 
                    self.current_graphics_item.pos().y()
                )
        
        elif prop_name == 'y':
            y_mm = UnitConverter.unit_to_mm(value, current_unit)
            self.current_element.config.y = y_mm
            
            logger.debug(f"[PROP-PANEL] Y changed: {value:.2f}{current_unit.value} = {y_mm:.2f}mm")
            
            if self.current_graphics_item:
                y_px = int(y_mm * self.current_graphics_item.dpi / 25.4)
                self.current_graphics_item.setPos(
                    self.current_graphics_item.pos().x(),
                    y_px
                )
        
        elif prop_name == 'text':
            self.current_element.text = value
            if self.current_graphics_item:
                self.current_graphics_item.update_text(value)
        
        elif prop_name == 'font_size':
            self.current_element.font_size = value
            if self.current_graphics_item:
                self.current_graphics_item.update_font_size(value)
        
        elif prop_name == 'data_field':
            self.current_element.data_field = value
            if self.current_graphics_item:
                self.current_graphics_item.update_display_text()
        
        elif prop_name == 'barcode_data':
            self.current_element.data = value
        
        elif prop_name == 'barcode_width':
            self.current_element.width = value
            if self.current_graphics_item:
                self.current_graphics_item.update_size(value, self.current_element.height)
        
        elif prop_name == 'barcode_height':
            self.current_element.height = value
            if self.current_graphics_item:
                self.current_graphics_item.update_size(self.current_element.width, value)
        
        elif prop_name == 'barcode_data_field':
            self.current_element.data_field = value
        
        elif prop_name == 'shape_width':
            self.current_element.config.width = value
            if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_from_element'):
                self.current_graphics_item.update_from_element()
        
        elif prop_name == 'shape_height':
            self.current_element.config.height = value
            if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_from_element'):
                self.current_graphics_item.update_from_element()
        
        elif prop_name == 'shape_fill':
            self.current_element.config.fill = value
            if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_from_element'):
                self.current_graphics_item.update_from_element()
        
        elif prop_name == 'shape_thickness':
            if hasattr(self.current_element.config, 'border_thickness'):
                self.current_element.config.border_thickness = value
            elif hasattr(self.current_element.config, 'thickness'):
                # Line element
                self.current_element.config.thickness = value
            if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_from_element'):
                self.current_graphics_item.update_from_element()
        
        # Сигнал об изменении
        self.property_changed.emit(prop_name, value)
        
        logger.info(f"Property '{prop_name}' changed to '{value}'")
    
    def update_position(self, x_mm, y_mm):
        """Обновить позицию в UI (вызывается из position_changed сигнала)"""
        # Блокировать сигналы чтобы не вызвать _on_property_change
        self.x_input.blockSignals(True)
        self.y_input.blockSignals(True)
        
        self.x_input.setValue(x_mm)
        self.y_input.setValue(y_mm)
        
        self.x_input.blockSignals(False)
        self.y_input.blockSignals(False)
        
        logger.debug(f"PropertyPanel position updated: ({x_mm:.1f}, {y_mm:.1f})")
    
    def _on_bold_changed(self, state):
        """Обработка изменения Bold checkbox"""
        if self.current_element and hasattr(self.current_element, 'bold'):
            self.current_element.bold = (state == 2)  # 2 = Qt.Checked
            
            # Обновить графический item
            if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_display'):
                self.current_graphics_item.update_display()
            
            logger.debug(f"[PROP-PANEL] Bold changed: {self.current_element.bold}")
    
    def _on_underline_changed(self, state):
        """Обработка изменения Underline checkbox"""
        if self.current_element and hasattr(self.current_element, 'underline'):
            self.current_element.underline = (state == 2)  # 2 = Qt.Checked

            # Обновить графический item
            if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_display'):
                self.current_graphics_item.update_display()

            logger.debug(f"[PROP-PANEL] Underline changed: {self.current_element.underline}")

    def _on_font_selected(self, font: ZplFont):
        if not isinstance(self.current_element, TextElement):
            return

        text_element: TextElement = self.current_element
        text_element.config.font_code = font.code
        text_element.config.font_display_name = font.display_name

        if font.scalable:
            self.font_width_input.setVisible(True)
            self.font_multiplier_input.setVisible(False)
            text_element.config.font_multiplier = 1
        else:
            self.font_width_input.setVisible(False)
            self.font_multiplier_input.setVisible(True)
            if text_element.config.font_multiplier <= 0:
                text_element.config.font_multiplier = 1

        if self.current_graphics_item and hasattr(self.current_graphics_item, 'set_font'):
            self.current_graphics_item.set_font(font, text_element.config.font_multiplier)

        self.font_size_input.blockSignals(True)
        self.font_size_input.setValue(text_element.config.font_height_dots)
        self.font_size_input.blockSignals(False)

        if font.scalable:
            self.font_width_input.blockSignals(True)
            self.font_width_input.setValue(text_element.config.font_width_dots)
            self.font_width_input.blockSignals(False)
        else:
            self.font_multiplier_input.blockSignals(True)
            self.font_multiplier_input.setValue(text_element.config.font_multiplier)
            self.font_multiplier_input.blockSignals(False)

        logger.debug(f"[PROP-FONT] User selected: {font.code}")

    def _on_font_height_changed(self, value: int):
        if not isinstance(self.current_element, TextElement):
            return

        text_element: TextElement = self.current_element
        text_element.font_size = value
        text_element.config.font_height_dots = value

        if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_font_size'):
            self.current_graphics_item.update_font_size(value)

        logger.debug(f"[PROP-FONT] Height changed to {value} dots")

    def _on_font_width_changed(self, value: int):
        if not isinstance(self.current_element, TextElement):
            return

        text_element: TextElement = self.current_element
        text_element.config.font_width_dots = value

        if self.current_graphics_item and hasattr(self.current_graphics_item, 'update_display'):
            self.current_graphics_item.update_display()
            self.current_graphics_item.updateHandlesPos()

        logger.debug(f"[PROP-FONT] Width changed to {value} dots")

    def _on_font_multiplier_changed(self, value: int):
        if not isinstance(self.current_element, TextElement):
            return

        text_element: TextElement = self.current_element
        text_element.config.font_multiplier = value
        font_enum = ZplFont.by_code(text_element.config.font_code)

        if self.current_graphics_item and hasattr(self.current_graphics_item, 'set_font'):
            self.current_graphics_item.set_font(font_enum, value)

        logger.debug(f"[PROP-FONT] Multiplier changed to {value}")

    def _on_alignment_changed(self, alignment: TextAlignment):
        if not isinstance(self.current_element, TextElement):
            return

        self.current_element.config.alignment = alignment.key

        if self.current_graphics_item and hasattr(self.current_graphics_item, 'set_alignment'):
            self.current_graphics_item.set_alignment(alignment)

        logger.debug(f"[PROP-ALIGN] Alignment set to {alignment.key}")

    def _on_block_width_changed(self, value: float):
        if not isinstance(self.current_element, TextElement):
            return

        self.current_element.config.block_width_mm = value
        if self.current_graphics_item and hasattr(self.current_graphics_item, 'set_block_width_mm'):
            self.current_graphics_item.set_block_width_mm(value)

        logger.debug(f"[PROP-TEXT] Block width changed to {value}mm")

    def _on_text_box_changed(self, axis: str, value: float):
        if not isinstance(self.current_element, TextElement):
            return

        if axis == 'width':
            self.current_element.config.box_width_mm = value
        else:
            self.current_element.config.box_height_mm = value

        if self.current_graphics_item and hasattr(self.current_graphics_item, 'set_box_size'):
            if axis == 'width':
                self.current_graphics_item.set_box_size(width_mm=value)
            else:
                self.current_graphics_item.set_box_size(height_mm=value)

        logger.debug(f"[PROP-TEXT] Box {axis} changed to {value}mm")

    def _on_keep_aspect_ratio_changed(self, state):
        if not isinstance(self.current_element, TextElement):
            return

        enabled = state == 2
        self.current_element.config.keep_aspect_ratio = enabled
        if self.current_graphics_item and hasattr(self.current_graphics_item, 'set_keep_aspect_ratio'):
            self.current_graphics_item.set_keep_aspect_ratio(enabled)

        logger.debug(f"[PROP-TEXT] Keep aspect ratio: {enabled}")

    def _on_anchor_changed(self, anchor: AnchorPosition):
        if not isinstance(self.current_element, TextElement):
            return

        self.current_element.config.anchor_position = anchor.value
        if self.current_graphics_item and hasattr(self.current_graphics_item, 'change_anchor'):
            self.current_graphics_item.change_anchor(anchor)

        logger.debug(f"[PROP-TEXT] Anchor changed to {anchor.name}")

    def _on_text_size_changed(self, width_mm: float, height_mm: float):
        self.text_width_input.blockSignals(True)
        self.text_width_input.setValue(max(width_mm, 1.0))
        self.text_width_input.blockSignals(False)

        self.text_height_input.blockSignals(True)
        self.text_height_input.setValue(max(height_mm, 1.0))
        self.text_height_input.blockSignals(False)
    
    def _on_image_width_changed(self, value):
        """Оновити ширину зображення"""
        if self.current_element and hasattr(self.current_element.config, 'width'):
            logger.debug(f"[PROP-IMAGE] Width changed: {value}mm")
            self.current_element.config.width = value
            if self.current_graphics_item:
                self.current_graphics_item.update_from_element()
    
    def _on_image_height_changed(self, value):
        """Оновити висоту зображення"""
        if self.current_element and hasattr(self.current_element.config, 'height'):
            logger.debug(f"[PROP-IMAGE] Height changed: {value}mm")
            self.current_element.config.height = value
            if self.current_graphics_item:
                self.current_graphics_item.update_from_element()
    
    def _on_change_image(self):
        """Змінити зображення"""
        from PySide6.QtWidgets import QFileDialog
        import base64
        
        if not self.current_element:
            return
        
        logger.debug(f"[PROP-IMAGE] Opening change image dialog")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select New Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if not file_path:
            return
        
        logger.debug(f"[PROP-IMAGE] Selected new image: {file_path}")
        
        try:
            # Конвертувати у base64
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
                image_data = base64.b64encode(image_bytes).decode('utf-8')
            
            # Оновити element
            self.current_element.config.image_path = file_path
            self.current_element.config.image_data = image_data
            
            # Оновити graphics item
            if self.current_graphics_item:
                self.current_graphics_item.update_from_element()
            
            logger.info(f"Image changed: {file_path}")
            
        except Exception as e:
            logger.error(f"[PROP-IMAGE] Failed to change image: {e}")
    
    def _get_main_window(self):
        """Отримати MainWindow"""
        widget = self.parent()
        while widget and not hasattr(widget, 'current_unit'):
            widget = widget.parent()
        return widget
    
    def update_for_unit(self, new_unit):
        """Оновити PropertyPanel при зміні units (БЕЗ зміни element)"""
        if not self.current_element or not self.current_graphics_item:
            return
        
        # Просто викликати set_element знову
        self.set_element(self.current_element, self.current_graphics_item)
