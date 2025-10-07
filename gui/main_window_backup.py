# -*- coding: utf-8 -*-
"""Главное окно приложения"""

from PySide6.QtWidgets import (QMainWindow, QDockWidget, QMessageBox, 
                               QTextEdit, QDialog, QVBoxLayout, QLabel,
                               QInputDialog, QFileDialog, QWidget, QGridLayout, QToolTip, QCheckBox,
                               QDoubleSpinBox, QPushButton, QHBoxLayout, QComboBox)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPixmap, QCursor, QShortcut, QKeySequence, QUndoStack
from io import BytesIO
from .canvas_view import CanvasView
from .toolbar import EditorToolbar
from .property_panel import PropertyPanel
from .smart_guides import SmartGuides
from .rulers import HorizontalRuler, VerticalRuler
from core.elements.text_element import TextElement, GraphicsTextItem
from core.elements.image_element import ImageElement, GraphicsImageItem, ImageConfig
from core.undo_commands import (
    AddElementCommand, 
    DeleteElementCommand, 
    MoveElementCommand, 
    ChangePropertyCommand
)
from core.elements.base import ElementConfig
from core.template_manager import TemplateManager
from zpl.generator import ZPLGenerator
from integration.labelary_client import LabelaryClient
from utils.logger import logger
from utils.unit_converter import MeasurementUnit, UnitConverter
from config import DEFAULT_UNIT, UNIT_DECIMALS, UNIT_STEPS

class MainWindow(QMainWindow):
    """Главное окно редактора"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZPL Label Designer")
        self.resize(1200, 700)
        logger.info("MainWindow initialized")
        
        # Список элементов и графических элементов
        self.elements = []
        self.graphics_items = []
        self.selected_item = None
        
        # Clipboard для copy/paste
        self.clipboard_element = None
        
        # ZPL Generator
        self.zpl_generator = ZPLGenerator(dpi=203)
        self.labelary_client = LabelaryClient(dpi=203)
        self.template_manager = TemplateManager()
        logger.info("ZPL Generator, Labelary Client and Template Manager created")
        
        # Создать canvas
        self.canvas = CanvasView(width_mm=28, height_mm=28, dpi=203)
        logger.info("Canvas created (28x28mm, DPI 203)")
        
        # Smart Guides (ПОСЛЕ создания canvas!)
        self.smart_guides = SmartGuides(self.canvas.scene)
        self.guides_enabled = True
        logger.info("Smart Guides initialized")
        
        # Undo/Redo Stack
        self.undo_stack = QUndoStack(self)
        logger.debug(f"[UNDO-STACK] Initialized")
        
        # Зберігати позицію перед drag для MoveCommand
        self.drag_start_pos = None
        
        # Создать линейки
        self.h_ruler = HorizontalRuler(length_mm=28, dpi=203, scale=2.5)
        self.v_ruler = VerticalRuler(length_mm=28, dpi=203, scale=2.5)
        logger.info("Rulers created")
        
        # Встановити посилання на rulers у canvas
        self.canvas.h_ruler = self.h_ruler
        self.canvas.v_ruler = self.v_ruler
        logger.info("Rulers linked to canvas")
        
        # Создать central widget с layout
        central_widget = QWidget()
        grid_layout = QGridLayout(central_widget)
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Добавить в layout: [пусто] [h_ruler]
        #                     [v_ruler] [canvas]
        corner_spacer = QWidget()
        corner_spacer.setFixedSize(25, 25)
        grid_layout.addWidget(corner_spacer, 0, 0)
        grid_layout.addWidget(self.h_ruler, 0, 1)
        grid_layout.addWidget(self.v_ruler, 1, 0)
        grid_layout.addWidget(self.canvas, 1, 1)
        
        self.setCentralWidget(central_widget)
        logger.info("Central widget with rulers configured")
        
        # Создать toolbar
        self.toolbar = EditorToolbar(self)
        self.addToolBar(self.toolbar)
        logger.info("Toolbar created")
        
        # Создать property panel
        self.property_panel = PropertyPanel()
        dock = QDockWidget("Properties", self)
        dock.setWidget(self.property_panel)
        dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        logger.info("Property panel created")
        
        # Подключить сигналы canvas
        self.canvas.scene.selectionChanged.connect(self._on_selection_changed)
        
        # Подключить сигналы toolbar
        self.toolbar.add_text_action.triggered.connect(self._add_text)
        self.toolbar.add_ean13_action.triggered.connect(self._add_ean13)
        self.toolbar.add_code128_action.triggered.connect(self._add_code128)
        self.toolbar.add_qrcode_action.triggered.connect(self._add_qrcode)
        self.toolbar.add_rectangle_action.triggered.connect(self._add_rectangle)
        self.toolbar.add_circle_action.triggered.connect(self._add_circle)
        self.toolbar.add_line_action.triggered.connect(self._add_line)
        self.toolbar.add_image_action.triggered.connect(self._add_image)
        self.toolbar.save_action.triggered.connect(self._save_template)
        self.toolbar.load_action.triggered.connect(self._load_template)
        self.toolbar.export_action.triggered.connect(self._export_zpl)
        self.toolbar.preview_action.triggered.connect(self._show_preview)
        logger.info("Signals connected")
        
        # Підключити cursor tracking
        self.canvas.cursor_position_changed.connect(self._update_ruler_cursor)
        self.canvas.context_menu_requested.connect(self._show_context_menu)
        
        # Відслідковувати коли курсор виходить з canvas
        self.canvas.viewport().installEventFilter(self)
        self.canvas.scene.installEventFilter(self)
        logger.info("Cursor tracking and scene events connected")
        
        # Keyboard shortcuts для zoom
        self._setup_shortcuts()
        logger.info("Keyboard shortcuts configured")
        
        # Snap to grid
        self.snap_enabled = True
        self._create_snap_toggle()
        
        # Current display unit
        self.current_unit = DEFAULT_UNIT
        
        # Label size controls
        self._create_label_size_controls()
        
        # Units controls
        self._create_units_controls()
    
    def _undo(self):
        """Отменить последнюю операцию"""
        if self.undo_stack.canUndo():
            logger.debug(f"[UNDO-ACTION] Undo: {self.undo_stack.undoText()}")
            self.undo_stack.undo()
        else:
            logger.debug(f"[UNDO-ACTION] Nothing to undo")
    
    def _redo(self):
        """Повторить отмененную операцию"""
        if self.undo_stack.canRedo():
            logger.debug(f"[UNDO-ACTION] Redo: {self.undo_stack.redoText()}")
            self.undo_stack.redo()
        else:
            logger.debug(f"[UNDO-ACTION] Nothing to redo")
    
    def _add_text(self):
        """Добавить текстовый элемент"""
        # Создать элемент
        config = ElementConfig(x=10, y=10)
        text_element = TextElement(config, "New Text", font_size=25)
        
        # Создать графический элемент
        graphics_item = GraphicsTextItem(
            text_element,
            dpi=self.canvas.dpi,
            canvas=self.canvas,
        )
        # Установить snap согласно текущему состоянию
        graphics_item.snap_enabled = self.snap_enabled
        
        # Добавить через UndoCommand
        command = AddElementCommand(self, text_element, graphics_item)
        self.undo_stack.push(command)
        
        logger.info(f"Text added at ({text_element.config.x}, {text_element.config.y})")
    
    def _add_ean13(self):
        """Добавить EAN-13 штрихкод"""
        from core.elements.barcode_element import EAN13BarcodeElement, GraphicsBarcodeItem
        
        config = ElementConfig(x=10, y=10)
        element = EAN13BarcodeElement(config, data='1234567890123', width=20, height=10)
        
        graphics_item = GraphicsBarcodeItem(element, dpi=self.canvas.dpi)
        graphics_item.snap_enabled = self.snap_enabled
        self.canvas.scene.addItem(graphics_item)
        
        self.elements.append(element)
        self.graphics_items.append(graphics_item)
        
        logger.info(f"EAN-13 barcode added at ({element.config.x}, {element.config.y})")
    
    def _add_code128(self):
        """Добавить Code 128 штрихкод"""
        from core.elements.barcode_element import Code128BarcodeElement, GraphicsBarcodeItem
        
        config = ElementConfig(x=10, y=10)
        element = Code128BarcodeElement(config, data='SAMPLE128', width=30, height=10)
        
        graphics_item = GraphicsBarcodeItem(element, dpi=self.canvas.dpi)
        graphics_item.snap_enabled = self.snap_enabled
        self.canvas.scene.addItem(graphics_item)
        
        self.elements.append(element)
        self.graphics_items.append(graphics_item)
        
        logger.info(f"Code 128 barcode added at ({element.config.x}, {element.config.y})")
    
    def _add_qrcode(self):
        """Добавить QR Code"""
        from core.elements.barcode_element import QRCodeElement, GraphicsBarcodeItem
        
        config = ElementConfig(x=10, y=10)
        element = QRCodeElement(config, data='https://example.com', size=15)
        
        graphics_item = GraphicsBarcodeItem(element, dpi=self.canvas.dpi)
        graphics_item.snap_enabled = self.snap_enabled
        self.canvas.scene.addItem(graphics_item)
        
        self.elements.append(element)
        self.graphics_items.append(graphics_item)
        
        logger.info(f"QR Code added at ({element.config.x}, {element.config.y})")
    
    def _add_rectangle(self):
        """Додати Rectangle"""
        from core.elements.shape_element import RectangleElement, ShapeConfig, GraphicsRectangleItem
        
        config = ShapeConfig(x=10, y=10, width=20, height=10, fill=False, border_thickness=2)
        element = RectangleElement(config)
        
        graphics_item = GraphicsRectangleItem(element, dpi=self.canvas.dpi)
        graphics_item.snap_enabled = self.snap_enabled
        self.canvas.scene.addItem(graphics_item)
        
        self.elements.append(element)
        self.graphics_items.append(graphics_item)
        
        logger.info(f"Rectangle added at ({element.config.x}, {element.config.y})mm, size=({element.config.width}x{element.config.height})mm")
    
    def _add_circle(self):
        """Додати Circle"""
        from core.elements.shape_element import CircleElement, ShapeConfig, GraphicsCircleItem
        
        config = ShapeConfig(x=10, y=10, width=15, height=15, fill=False, border_thickness=2)
        element = CircleElement(config)
        
        graphics_item = GraphicsCircleItem(element, dpi=self.canvas.dpi)
        graphics_item.snap_enabled = self.snap_enabled
        self.canvas.scene.addItem(graphics_item)
        
        self.elements.append(element)
        self.graphics_items.append(graphics_item)
        
        logger.info(f"Circle added at ({element.config.x}, {element.config.y})mm, size=({element.config.width}x{element.config.height})mm")
    
    def _add_line(self):
        """Додати Line"""
        from core.elements.shape_element import LineElement, LineConfig, GraphicsLineItem
        
        config = LineConfig(x=10, y=10, x2=25, y2=20, thickness=2)
        element = LineElement(config)
        
        graphics_item = GraphicsLineItem(element, dpi=self.canvas.dpi)
        graphics_item.snap_enabled = self.snap_enabled
        self.canvas.scene.addItem(graphics_item)
        
        self.elements.append(element)
        self.graphics_items.append(graphics_item)
        
        logger.info(f"Line added from ({element.config.x}, {element.config.y})mm to ({element.config.x2}, {element.config.y2})mm")
    
    def _add_image(self):
        """Додати Image елемент"""
        import base64
        
        logger.debug(f"[ADD-IMAGE] Opening file dialog")
        
        # Діалог вибору файлу
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if not file_path:
            logger.debug(f"[ADD-IMAGE] No file selected")
            return
        
        logger.debug(f"[ADD-IMAGE] Selected file: {file_path}")
        
        # Конвертувати зображення у base64
        try:
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
                image_data = base64.b64encode(image_bytes).decode('utf-8')
            
            logger.debug(f"[ADD-IMAGE] Image data length: {len(image_data)} chars")
            
            # Створити ImageElement
            config = ImageConfig(
                x=10.0,
                y=10.0,
                width=30.0,  # 30mm default
                height=30.0,
                image_path=file_path,
                image_data=image_data
            )
            image_element = ImageElement(config)
            
            # Створити graphics item
            graphics_item = GraphicsImageItem(image_element, dpi=self.canvas.dpi)
            graphics_item.snap_enabled = self.snap_enabled
            
            # Додати через UndoCommand
            command = AddElementCommand(self, image_element, graphics_item)
            self.undo_stack.push(command)
            
            logger.info(f"Image added: {file_path}")
            
        except Exception as e:
            logger.error(f"[ADD-IMAGE] Failed to load image: {e}", exc_info=True)
            QMessageBox.critical(self, "Add Image", f"Failed to load image:\n{e}")
    
    def _on_selection_changed(self):
        """Обработка изменения выделения"""
        selected = self.canvas.scene.selectedItems()
        
        if len(selected) == 1:
            # Одиночне виділення
            graphics_item = selected[0]
            
            if hasattr(graphics_item, 'element'):
                element = graphics_item.element
                self.selected_item = graphics_item
                self.property_panel.set_element(element, graphics_item)
                
                # Підсвітити bounds на лінейках
                self._highlight_element_bounds(graphics_item)
                
                logger.info(f"Selected element at ({element.config.x:.1f}, {element.config.y:.1f})")
        
        elif len(selected) > 1:
            # Множинне виділення
            logger.debug(f"[MULTI-SELECT] {len(selected)} items selected")
            self.selected_item = None
            self.property_panel.set_element(None, None)
            self.h_ruler.clear_highlight()
            self.v_ruler.clear_highlight()
            logger.info(f"Multi-select: {len(selected)} elements")
        
        else:
            # Очистити підсвічування
            self.h_ruler.clear_highlight()
            self.v_ruler.clear_highlight()
            self.selected_item = None
            self.property_panel.set_element(None, None)
            logger.debug("Selection cleared")
    
    def _export_zpl(self):
        """Экспорт в ZPL"""
        if not self.elements:
            logger.warning("Export ZPL: No elements to export")
            QMessageBox.warning(self, "Export", "No elements to export")
            return
        
        # Генерировать ZPL
        label_config = {
            'width': self.canvas.width_mm,
            'height': self.canvas.height_mm,
            'dpi': self.canvas.dpi
        }
        
        zpl_code = self.zpl_generator.generate(self.elements, label_config)
        logger.info("ZPL code generated for export")
        
        # Показать в диалоге
        dialog = QDialog(self)
        dialog.setWindowTitle("ZPL Code")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(zpl_code)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        dialog.setLayout(layout)
        
        dialog.exec()
        
        logger.info("ZPL export dialog shown")
    
    def _save_template(self):
        """Сохранить шаблон в JSON"""
        if not self.elements:
            logger.warning("Save template: No elements to save")
            QMessageBox.warning(self, "Save", "No elements to save")
            return
        
        # Диалог выбора пути для сохранения
        default_path = str(self.template_manager.templates_dir / "my_template.json")
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template",
            default_path,
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        # Убедиться что расширение .json
        if not filepath.endswith('.json'):
            filepath += '.json'
        
        # Извлечь имя шаблона из пути
        from pathlib import Path
        template_name = Path(filepath).stem
        
        # Подготовить конфигурацию
        label_config = {
            'width': self.canvas.width_mm,
            'height': self.canvas.height_mm,
            'dpi': self.canvas.dpi
        }
        
        # Метаданные
        metadata = {
            'elements_count': len(self.elements),
            'application': 'ZPL Label Designer 1.0'
        }
        
        try:
            # Создать структуру JSON напрямую
            from datetime import datetime
            import json
            
            template_data = {
                "name": template_name,
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "label_config": {
                    "width_mm": label_config.get('width', 28),
                    "height_mm": label_config.get('height', 28),
                    "dpi": label_config.get('dpi', 203),
                    "display_unit": self.current_unit.value  # ← зберегти display_unit
                },
                "elements": [element.to_dict() for element in self.elements],
                "metadata": metadata
            }
            
            logger.info(f"[TEMPLATE] Saving with display_unit: {self.current_unit.value}")
            
            # Сохранить в выбранный файл
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Template saved: {filepath}")
            QMessageBox.information(
                self, 
                "Save", 
                f"Template saved successfully!\n{filepath}"
            )
        
        except Exception as e:
            logger.error(f"Failed to save template: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                "Save Error", 
                f"Failed to save template:\n{e}"
            )
    
    def _load_template(self):
        """Загрузить шаблон из JSON"""
        # Открыть диалог выбора файла
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Template",
            str(self.template_manager.templates_dir),
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        try:
            # Загрузить шаблон
            template_data = self.template_manager.load_template(filepath)
            
            # Очистить текущий canvas (с перемалеванием сетки)
            self.canvas.clear_and_redraw_grid()
            self.elements.clear()
            self.graphics_items.clear()
            
            # Застосувати display_unit з template
            display_unit = template_data.get('display_unit', MeasurementUnit.MM)
            
            # Встановити units ComboBox
            index = self.units_combobox.findData(display_unit)
            if index >= 0:
                self.units_combobox.setCurrentIndex(index)
                # Викличе _on_unit_changed автоматично
            
            logger.info(f"[TEMPLATE] Applied display_unit: {display_unit.value}")
            
            # Обновить конфигурацию canvas (если нужно)
            label_config = template_data['label_config']
            width_mm = label_config.get('width_mm', 28)
            height_mm = label_config.get('height_mm', 28)
            
            logger.debug(f"[LOAD-TEMPLATE] Label size from template: {width_mm}x{height_mm}mm")
            
            # Застосувати розмір якщо відрізняється
            if width_mm != self.canvas.width_mm or height_mm != self.canvas.height_mm:
                logger.info(f"[LOAD-TEMPLATE] Applying new label size: {width_mm}x{height_mm}mm")
                self.canvas.set_label_size(width_mm, height_mm)
                self.h_ruler.set_length(width_mm)
                self.v_ruler.set_length(height_mm)
                
                # Оновити spinboxes
                self.width_spinbox.blockSignals(True)
                self.height_spinbox.blockSignals(True)
                self.width_spinbox.setValue(width_mm)
                self.height_spinbox.setValue(height_mm)
                self.width_spinbox.blockSignals(False)
                self.height_spinbox.blockSignals(False)
                
                logger.debug(f"[LOAD-TEMPLATE] Spinboxes updated: W={width_mm}, H={height_mm}")
            
            # Добавить элементы на canvas
            from core.elements.barcode_element import BarcodeElement, GraphicsBarcodeItem
            
            for element in template_data['elements']:
                # Создать графический элемент
                if isinstance(element, TextElement):
                    graphics_item = GraphicsTextItem(
                        element,
                        dpi=self.canvas.dpi,
                        canvas=self.canvas,
                    )
                elif isinstance(element, BarcodeElement):
                    graphics_item = GraphicsBarcodeItem(element, dpi=self.canvas.dpi)
                elif isinstance(element, ImageElement):
                    graphics_item = GraphicsImageItem(element, dpi=self.canvas.dpi)
                else:
                    continue
                
                self.canvas.scene.addItem(graphics_item)
                
                # Сохранить
                self.elements.append(element)
                self.graphics_items.append(graphics_item)
            
            logger.info(f"Template loaded: {filepath} ({len(self.elements)} elements)")
            QMessageBox.information(
                self,
                "Load",
                f"Template loaded successfully!\n{len(self.elements)} elements"
            )
        
        except Exception as e:
            logger.error(f"Failed to load template: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load template:\n{e}"
            )
    
    def _highlight_element_bounds(self, item):
        """Підсвітити межі елемента на лінейках"""
        if hasattr(item, 'element'):
            element = item.element
            x = element.config.x
            y = element.config.y
            
            # Отримати розміри з boundingRect
            bounds = item.boundingRect()
            width_px = bounds.width()
            height_px = bounds.height()
            
            # Конвертувати у мм
            dpi = 203
            width_mm = width_px * 25.4 / dpi
            height_mm = height_px * 25.4 / dpi
            
            logger.debug(f"[BOUNDS] Element at: x={x:.2f}mm, y={y:.2f}mm")
            logger.debug(f"[BOUNDS] Size: width={width_mm:.2f}mm, height={height_mm:.2f}mm")
            
            # Підсвітити на лінейках
            self.h_ruler.highlight_bounds(x, width_mm)
            self.v_ruler.highlight_bounds(y, height_mm)
            logger.info(f"Highlighted bounds: X={x}mm W={width_mm:.1f}mm, Y={y}mm H={height_mm:.1f}mm")
    
    def _update_ruler_cursor(self, x_mm, y_mm):
        """Оновити cursor markers на лінейках"""
        self.h_ruler.update_cursor_position(x_mm)
        self.v_ruler.update_cursor_position(y_mm)
        
        # Показати tooltip
        self._show_cursor_tooltip(x_mm, y_mm)
    
    def _show_cursor_tooltip(self, x_mm, y_mm):
        """Показати tooltip з координатами"""
        tooltip_text = f"X: {x_mm:.1f} mm\nY: {y_mm:.1f} mm"
        QToolTip.showText(QCursor.pos(), tooltip_text)
    
    def eventFilter(self, obj, event):
        """Обробка подій canvas та scene"""
        if obj == self.canvas.viewport():
            if event.type() == QEvent.Leave:
                self.h_ruler.hide_cursor()
                self.v_ruler.hide_cursor()
            # ПРОПУСТИТИ wheel події далі до CanvasView
            elif event.type() == QEvent.Wheel:
                return False  # НЕ блокувати, пропустити
        
        elif obj == self.canvas.scene:
            # Зберегти позицію для MoveCommand
            if event.type() == QEvent.GraphicsSceneMousePress:
                items = self.canvas.scene.items(event.scenePos())
                item = items[0] if items else None
                
                if item and hasattr(item, 'element'):
                    self.drag_start_pos = (item.element.config.x, item.element.config.y)
                    logger.debug(f"[DRAG-START] Pos: ({self.drag_start_pos[0]:.2f}, {self.drag_start_pos[1]:.2f})")
                else:
                    self.drag_start_pos = None
            
            # Smart Guides під час drag
            elif event.type() == QEvent.GraphicsSceneMouseMove:
                # Отримати item під курсором
                items = self.canvas.scene.items(event.scenePos())
                dragged_item = items[0] if items else None
                
                if self.guides_enabled and dragged_item and hasattr(dragged_item, 'element'):
                    snap_pos = self.smart_guides.check_alignment(
                        dragged_item,
                        self.graphics_items,
                        dpi=203
                    )
                    if snap_pos:
                        snap_x, snap_y = snap_pos
                        if snap_x is not None:
                            dragged_item.element.config.x = snap_x
                        if snap_y is not None:
                            dragged_item.element.config.y = snap_y
                        
                        # Оновити графічну позицію
                        dpi = 203
                        x_px = dragged_item.element.config.x * dpi / 25.4
                        y_px = dragged_item.element.config.y * dpi / 25.4
                        dragged_item.setPos(x_px, y_px)
            
            # Очистити guides після drag
            elif event.type() == QEvent.GraphicsSceneMouseRelease:
                # Створити MoveCommand якщо позиція змінилась
                items = self.canvas.scene.items(event.scenePos())
                item = items[0] if items else None
                
                if item and hasattr(item, 'element') and self.drag_start_pos:
                    old_x, old_y = self.drag_start_pos
                    new_x = item.element.config.x
                    new_y = item.element.config.y
                    
                    if abs(new_x - old_x) > 0.01 or abs(new_y - old_y) > 0.01:
                        logger.debug(f"[DRAG-END] Creating MoveCommand")
                        command = MoveElementCommand(item.element, item, old_x, old_y, new_x, new_y)
                        self.undo_stack.push(command)
                    
                    self.drag_start_pos = None
                
                self.smart_guides.clear_guides()
        
        return super().eventFilter(obj, event)
    
    def _setup_shortcuts(self):
        """Keyboard shortcuts"""
        # Zoom in
        zoom_in = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in.activated.connect(self.canvas.zoom_in)
        
        # Zoom in (альтернативна клавіша)
        zoom_in2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in2.activated.connect(self.canvas.zoom_in)
        
        # Zoom out
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(self.canvas.zoom_out)
        
        # Reset zoom
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset.activated.connect(self.canvas.reset_zoom)
        
        # Snap toggle
        snap_toggle = QShortcut(QKeySequence("Ctrl+G"), self)
        snap_toggle.activated.connect(lambda: self._toggle_snap(0 if self.snap_enabled else 2))
        
        # Font Styles - Bold
        bold_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        bold_shortcut.activated.connect(self._toggle_bold)
        
        # Font Styles - Underline
        underline_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        underline_shortcut.activated.connect(self._toggle_underline)
        
        # Bold toggle
        bold_toggle = QShortcut(QKeySequence("Ctrl+B"), self)
        bold_toggle.activated.connect(self._toggle_bold)
        
        # Underline toggle
        underline_toggle = QShortcut(QKeySequence("Ctrl+U"), self)
        underline_toggle.activated.connect(self._toggle_underline)
        
        logger.debug("Zoom shortcuts: Ctrl+Plus, Ctrl+Minus, Ctrl+0")
        logger.debug("Snap shortcut: Ctrl+G")
    
    def _toggle_guides(self, state):
        """Перемикач smart guides"""
        self.guides_enabled = (state == 2)
        self.smart_guides.set_enabled(self.guides_enabled)
        logger.debug(f"[GUIDES-TOGGLE] Enabled: {self.guides_enabled}")
    
    def _create_snap_toggle(self):
        """Створити toggle для snap to grid"""
        snap_checkbox = QCheckBox("Snap to Grid")
        snap_checkbox.setChecked(True)
        snap_checkbox.stateChanged.connect(self._toggle_snap)
        
        # Додати до toolbar
        self.toolbar.addSeparator()
        self.toolbar.addWidget(snap_checkbox)
        
        # Smart Guides checkbox
        guides_checkbox = QCheckBox("Smart Guides")
        guides_checkbox.setChecked(True)
        guides_checkbox.stateChanged.connect(self._toggle_guides)
        self.toolbar.addWidget(guides_checkbox)
        
        logger.info("Snap to Grid and Smart Guides toggles created")
        
        # КРИТИЧНО: викликати _toggle_snap щоб встановити snap для існуючих елементів
        self._toggle_snap(2)  # 2 = Qt.Checked
    
    def _toggle_snap(self, state):
        """Увімкнути/вимкнути snap"""
        # state це int: 0=Unchecked, 2=Checked
        self.snap_enabled = (state == 2)  # Qt.Checked = 2
        
        # Оновити всі елементи
        for item in self.graphics_items:
            if hasattr(item, 'snap_enabled'):
                item.snap_enabled = self.snap_enabled
        
        logger.info(f"Snap to Grid: {'ON' if self.snap_enabled else 'OFF'} (items: {len(self.graphics_items)})")
    
    def _toggle_bold(self):
        """Включить/выключить Bold для selected element"""
        if self.selected_item and hasattr(self.selected_item, 'element'):
            element = self.selected_item.element
            
            if hasattr(element, 'bold'):
                element.bold = not element.bold
                
                # Обновить графический item
                if hasattr(self.selected_item, 'update_display'):
                    self.selected_item.update_display()
                
                # Обновить PropertyPanel checkbox
                if self.property_panel.current_element == element:
                    self.property_panel.bold_checkbox.blockSignals(True)
                    self.property_panel.bold_checkbox.setChecked(element.bold)
                    self.property_panel.bold_checkbox.blockSignals(False)
                
                logger.debug(f"[SHORTCUT] Bold toggled: {element.bold}")
    
    def _toggle_underline(self):
        """Включить/выключить Underline для selected element"""
        if self.selected_item and hasattr(self.selected_item, 'element'):
            element = self.selected_item.element
            
            if hasattr(element, 'underline'):
                element.underline = not element.underline
                
                # Обновить графический item
                if hasattr(self.selected_item, 'update_display'):
                    self.selected_item.update_display()
                
                # Обновить PropertyPanel checkbox
                if self.property_panel.current_element == element:
                    self.property_panel.underline_checkbox.blockSignals(True)
                    self.property_panel.underline_checkbox.setChecked(element.underline)
                    self.property_panel.underline_checkbox.blockSignals(False)
                
                logger.debug(f"[SHORTCUT] Underline toggled: {element.underline}")
    
    def _move_selected(self, dx_mm, dy_mm):
        """Перемістити виділені елементи (підтримка multi-select)"""
        selected = self.canvas.scene.selectedItems()
        
        if len(selected) > 1:
            # Групове переміщення
            logger.debug(f"[MOVE-GROUP] Moving {len(selected)} items by ({dx_mm:.2f}, {dy_mm:.2f})mm")
            
            for item in selected:
                if hasattr(item, 'element'):
                    element = item.element
                    old_x, old_y = element.config.x, element.config.y
                    
                    element.config.x += dx_mm
                    element.config.y += dy_mm
                    
                    # Оновити позицію graphics item
                    dpi = 203
                    new_x = element.config.x * dpi / 25.4
                    new_y = element.config.y * dpi / 25.4
                    item.setPos(new_x, new_y)
                    
                    # Створити MoveCommand для undo
                    command = MoveElementCommand(element, item, old_x, old_y, element.config.x, element.config.y)
                    self.undo_stack.push(command)
            
            logger.info(f"Moved {len(selected)} elements by ({dx_mm}, {dy_mm})mm")
        
        elif self.selected_item and hasattr(self.selected_item, 'element'):
            # Одиночне переміщення
            element = self.selected_item.element
            old_x, old_y = element.config.x, element.config.y
            
            element.config.x += dx_mm
            element.config.y += dy_mm
            
            logger.debug(f"[MOVE] Before: ({old_x:.2f}, {old_y:.2f})mm")
            logger.debug(f"[MOVE] Delta: ({dx_mm:.2f}, {dy_mm:.2f})mm")
            logger.debug(f"[MOVE] After: ({element.config.x:.2f}, {element.config.y:.2f})mm")
            
            # Оновити позицію graphics item
            dpi = 203
            new_x = element.config.x * dpi / 25.4
            new_y = element.config.y * dpi / 25.4
            self.selected_item.setPos(new_x, new_y)
            
            # Оновити property panel та bounds
            if self.property_panel.current_element:
                self.property_panel.update_position(element.config.x, element.config.y)
            self._highlight_element_bounds(self.selected_item)
            
            logger.info(f"Element moved: dx={dx_mm}mm, dy={dy_mm}mm -> ({element.config.x}, {element.config.y})")
    
    def _copy_selected(self):
        """Копіювати виділений елемент у clipboard"""
        if self.selected_item and hasattr(self.selected_item, 'element'):
            import copy
            self.clipboard_element = copy.deepcopy(self.selected_item.element)
            logger.debug(f"[CLIPBOARD] Copied: {self.clipboard_element.__class__.__name__}")
            logger.info(f"Element copied to clipboard")
    
    def _paste_from_clipboard(self):
        """Вставити елемент з clipboard"""
        if not self.clipboard_element:
            logger.debug(f"[CLIPBOARD] Empty - nothing to paste")
            return
        
        import copy
        new_element = copy.deepcopy(self.clipboard_element)
        
        # Offset для візуального розрізнення
        new_element.config.x += 5.0
        new_element.config.y += 5.0
        
        logger.debug(f"[CLIPBOARD] Paste at: ({new_element.config.x:.2f}, {new_element.config.y:.2f})mm")
        
        # Додати на canvas
        graphics_item = self._create_graphics_item(new_element)
        self.canvas.scene.addItem(graphics_item)
        self.elements.append(new_element)
        self.graphics_items.append(graphics_item)
        
        # Виділити новий item
        self.canvas.scene.clearSelection()
        graphics_item.setSelected(True)
        
        logger.info(f"Element pasted from clipboard")
    
    def _create_graphics_item(self, element):
        """Створити graphics item для елемента"""
        if isinstance(element, TextElement):
            graphics_item = GraphicsTextItem(
                element,
                dpi=self.canvas.dpi,
                canvas=self.canvas,
            )
        else:
            from core.elements.barcode_element import BarcodeElement, GraphicsBarcodeItem
            if isinstance(element, BarcodeElement):
                graphics_item = GraphicsBarcodeItem(element, dpi=self.canvas.dpi)
            else:
                return None
        
        graphics_item.snap_enabled = self.snap_enabled
        return graphics_item
    
    def _duplicate_selected(self):
        """Дублювати виділений елемент (Copy + Paste)"""
        if self.selected_item:
            logger.debug(f"[DUPLICATE] Start")
            self._copy_selected()
            self._paste_from_clipboard()
            logger.info(f"Element duplicated")
    
    def _bring_to_front(self):
        """Перемістити на передній план (z-order)"""
        if self.selected_item:
            max_z = max([item.zValue() for item in self.graphics_items], default=0)
            self.selected_item.setZValue(max_z + 1)
            logger.debug(f"[Z-ORDER] Bring to front: z={max_z + 1}")
            logger.info(f"Element brought to front")
    
    def _send_to_back(self):
        """Перемістити на задній план (z-order)"""
        if self.selected_item:
            min_z = min([item.zValue() for item in self.graphics_items], default=0)
            self.selected_item.setZValue(min_z - 1)
            logger.debug(f"[Z-ORDER] Send to back: z={min_z - 1}")
            logger.info(f"Element sent to back")
    
    def _show_context_menu(self, item, global_pos):
        """Показати context menu"""
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        if item:  # Item context menu
            logger.debug(f"[CONTEXT-MENU] Creating item menu")
            
            copy_action = menu.addAction("Copy (Ctrl+C)")
            copy_action.triggered.connect(self._copy_selected)
            
            duplicate_action = menu.addAction("Duplicate (Ctrl+D)")
            duplicate_action.triggered.connect(self._duplicate_selected)
            
            menu.addSeparator()
            
            front_action = menu.addAction("Bring to Front")
            front_action.triggered.connect(self._bring_to_front)
            
            back_action = menu.addAction("Send to Back")
            back_action.triggered.connect(self._send_to_back)
            
            menu.addSeparator()
            
            delete_action = menu.addAction("Delete (Del)")
            delete_action.triggered.connect(self._delete_selected)
        else:  # Canvas context menu
            logger.debug(f"[CONTEXT-MENU] Creating canvas menu")
            
            paste_action = menu.addAction("Paste (Ctrl+V)")
            paste_action.triggered.connect(self._paste_from_clipboard)
            paste_action.setEnabled(self.clipboard_element is not None)
        
        logger.debug(f"[CONTEXT-MENU] Show at: {global_pos}")
        menu.exec(global_pos)
    
    def _delete_selected(self):
        """Видалити виділені елементи (підтримка multi-select)"""
        selected = self.canvas.scene.selectedItems()
        
        if len(selected) > 1:
            # Групове видалення
            logger.debug(f"[DELETE-GROUP] Deleting {len(selected)} items")
            
            for item in selected:
                if hasattr(item, 'element'):
                    element = item.element
                    command = DeleteElementCommand(self, element, item)
                    self.undo_stack.push(command)
            
            # Очистити UI
            self.selected_item = None
            self.h_ruler.clear_highlight()
            self.v_ruler.clear_highlight()
            self.property_panel.set_element(None, None)
            logger.info(f"Deleted {len(selected)} elements")
        
        elif self.selected_item:
            # Одиночне видалення
            # Зберегти ПЕРЕД removeItem (race condition!)
            item_to_delete = self.selected_item
            element_to_delete = item_to_delete.element if hasattr(item_to_delete, 'element') else None
            
            if element_to_delete:
                logger.debug(f"[DELETE] Creating DeleteCommand")
                command = DeleteElementCommand(self, element_to_delete, item_to_delete)
                self.undo_stack.push(command)
                
                # Очистити UI
                self.selected_item = None
                self.h_ruler.clear_highlight()
                self.v_ruler.clear_highlight()
                self.property_panel.set_element(None, None)
                logger.debug(f"[DELETE] UI cleared")
    
    def keyPressEvent(self, event):
        """Keyboard shortcuts"""
        modifiers = event.modifiers()
        key = event.key()
        
        # === ZOOM ===
        if modifiers == Qt.ControlModifier:
            if key in (Qt.Key_Plus, Qt.Key_Equal):
                logger.debug("[SHORTCUT] Ctrl+Plus - Zoom In")
                self.canvas.zoom_in()
            elif key == Qt.Key_Minus:
                logger.debug("[SHORTCUT] Ctrl+Minus - Zoom Out")
                self.canvas.zoom_out()
            elif key == Qt.Key_0:
                logger.debug("[SHORTCUT] Ctrl+0 - Reset Zoom")
                self.canvas.reset_zoom()
            # === SNAP ===
            elif key == Qt.Key_G:
                logger.debug("[SHORTCUT] Ctrl+G - Toggle Snap")
                self.snap_enabled = not self.snap_enabled
                self._toggle_snap(Qt.Checked if self.snap_enabled else Qt.Unchecked)
            # === CLIPBOARD ===
            elif key == Qt.Key_C:
                logger.debug("[SHORTCUT] Ctrl+C - Copy")
                self._copy_selected()
            elif key == Qt.Key_V:
                logger.debug("[SHORTCUT] Ctrl+V - Paste")
                self._paste_from_clipboard()
            elif key == Qt.Key_D:
                logger.debug("[SHORTCUT] Ctrl+D - Duplicate")
                self._duplicate_selected()
            # === UNDO/REDO ===
            elif key == Qt.Key_Z:
                logger.debug("[SHORTCUT] Ctrl+Z - Undo")
                self._undo()
            elif key == Qt.Key_Y:
                logger.debug("[SHORTCUT] Ctrl+Y - Redo")
                self._redo()
        
        # === DELETE ===
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            logger.debug(f"[SHORTCUT] {event.key()} - Delete Element")
            self._delete_selected()
        
        # === PRECISION MOVE (Shift + Arrow) ===
        elif modifiers == Qt.ShiftModifier:
            if key == Qt.Key_Left:
                logger.debug("[SHORTCUT] Shift+Left - Move -0.1mm")
                self._move_selected(-0.1, 0)
            elif key == Qt.Key_Right:
                logger.debug("[SHORTCUT] Shift+Right - Move +0.1mm")
                self._move_selected(0.1, 0)
            elif key == Qt.Key_Up:
                logger.debug("[SHORTCUT] Shift+Up - Move -0.1mm")
                self._move_selected(0, -0.1)
            elif key == Qt.Key_Down:
                logger.debug("[SHORTCUT] Shift+Down - Move +0.1mm")
                self._move_selected(0, 0.1)
        
        # === NORMAL MOVE (Arrow) ===
        elif modifiers == Qt.NoModifier:
            if key == Qt.Key_Left:
                logger.debug("[SHORTCUT] Left - Move -1mm")
                self._move_selected(-1, 0)
            elif key == Qt.Key_Right:
                logger.debug("[SHORTCUT] Right - Move +1mm")
                self._move_selected(1, 0)
            elif key == Qt.Key_Up:
                logger.debug("[SHORTCUT] Up - Move -1mm")
                self._move_selected(0, -1)
            elif key == Qt.Key_Down:
                logger.debug("[SHORTCUT] Down - Move +1mm")
                self._move_selected(0, 1)
        
        super().keyPressEvent(event)
    
    def _show_preview(self):
        """Показать preview через Labelary"""
        logger.info("="*60)
        logger.info("PREVIEW REQUEST INITIATED")
        logger.info("="*60)
        
        if not self.elements:
            logger.warning("Preview aborted: No elements on canvas")
            QMessageBox.warning(self, "Preview", "No elements to preview")
            return
        
        # Информация об элементах
        logger.info(f"Elements count: {len(self.elements)}")
        for i, element in enumerate(self.elements):
            element_info = f"Element {i+1}: type={element.__class__.__name__}"
            if hasattr(element, 'text'):
                element_info += f", text='{element.text}'"
            if hasattr(element, 'font_size'):
                element_info += f", font_size={element.font_size}"
            element_info += f", position=({element.config.x:.1f}, {element.config.y:.1f})"
            if hasattr(element, 'data_field') and element.data_field:
                element_info += f", placeholder='{element.data_field}'"
            logger.info(element_info)
        
        # Генерировать ZPL
        label_config = {
            'width': self.canvas.width_mm,
            'height': self.canvas.height_mm,
            'dpi': self.canvas.dpi
        }
        logger.info(f"Label config: {label_config}")
        
        # Для preview заменить placeholder'ы на тестовые данные
        test_data = {}
        for element in self.elements:
            if hasattr(element, 'data_field') and element.data_field:
                # Извлечь имя поля из {{FIELD_NAME}}
                field_name = element.data_field.replace('{{', '').replace('}}', '')
                test_data[field_name] = '[TEST_DATA]'
        
        if test_data:
            logger.info(f"Test data for placeholders: {test_data}")
        else:
            logger.info("No placeholders, using actual text values")
        
        logger.info("Generating ZPL code...")
        zpl_code = self.zpl_generator.generate(self.elements, label_config, test_data)
        
        # Показать ZPL в DEBUG режиме
        logger.debug("="*60)
        logger.debug("GENERATED ZPL CODE:")
        logger.debug("="*60)
        for line in zpl_code.split('\n'):
            logger.debug(line)
        logger.debug("="*60)
        
        # Получить preview
        logger.info("Requesting preview from Labelary API...")
        try:
            image = self.labelary_client.preview(
                zpl_code,
                self.canvas.width_mm,
                self.canvas.height_mm
            )
            
            if image:
                logger.info("Preview image received, displaying dialog")
                
                # Показать preview
                dialog = QDialog(self)
                dialog.setWindowTitle("Preview")
                
                layout = QVBoxLayout()
                label = QLabel()
                
                # Конвертировать PIL Image -> QPixmap
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                pixmap = QPixmap()
                pixmap.loadFromData(image_bytes.getvalue())
                
                logger.info(f"Image size: {pixmap.width()}x{pixmap.height()}px")
                
                # Масштабировать для отображения
                pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(pixmap)
                
                layout.addWidget(label)
                dialog.setLayout(layout)
                dialog.resize(450, 450)
                dialog.exec()
                
                logger.info("Preview dialog closed")
                logger.info("="*60)
            else:
                logger.error("Preview failed: Labelary client returned None")
                logger.info("="*60)
                QMessageBox.critical(self, "Preview", "Failed to generate preview. Check logs for details.")
                
        except Exception as e:
            logger.error("="*60)
            logger.error("PREVIEW EXCEPTION")
            logger.error("="*60)
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {e}", exc_info=True)
            logger.error("="*60)
            QMessageBox.critical(self, "Preview", f"Failed to generate preview: {e}")

    def _create_label_size_controls(self):
        """Створити controls для зміни розміру етикетки"""
        from config import CONFIG
        
        # Container widget
        label_size_widget = QWidget()
        layout = QHBoxLayout(label_size_widget)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # Label
        layout.addWidget(QLabel("Label Size (mm):"))
        
        # Width SpinBox
        layout.addWidget(QLabel("W:"))
        self.width_spinbox = QDoubleSpinBox()
        self.width_spinbox.setRange(CONFIG['MIN_LABEL_WIDTH_MM'], CONFIG['MAX_LABEL_WIDTH_MM'])
        self.width_spinbox.setValue(self.canvas.width_mm)
        self.width_spinbox.setDecimals(1)
        self.width_spinbox.setSingleStep(1.0)
        self.width_spinbox.setFixedWidth(70)
        layout.addWidget(self.width_spinbox)
        
        # Height SpinBox
        layout.addWidget(QLabel("H:"))
        self.height_spinbox = QDoubleSpinBox()
        self.height_spinbox.setRange(CONFIG['MIN_LABEL_HEIGHT_MM'], CONFIG['MAX_LABEL_HEIGHT_MM'])
        self.height_spinbox.setValue(self.canvas.height_mm)
        self.height_spinbox.setDecimals(1)
        self.height_spinbox.setSingleStep(1.0)
        self.height_spinbox.setFixedWidth(70)
        layout.addWidget(self.height_spinbox)
        
        # Apply Button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply_label_size)
        apply_button.setFixedWidth(60)
        layout.addWidget(apply_button)
        
        # Додати до toolbar
        self.toolbar.addSeparator()
        self.toolbar.addWidget(label_size_widget)
        
        logger.info(f"Label Size controls created (range: {CONFIG['MIN_LABEL_WIDTH_MM']}-{CONFIG['MAX_LABEL_WIDTH_MM']}mm)")
    
    def _apply_label_size(self):
        """Застосувати новий розмір етикетки"""
        width_mm = self.width_spinbox.value()
        height_mm = self.height_spinbox.value()
        
        logger.debug(f"[SIZE-APPLY] User request: {width_mm}x{height_mm}mm")
        
        # Перевірити чи змінилось
        if width_mm == self.canvas.width_mm and height_mm == self.canvas.height_mm:
            logger.debug(f"[SIZE-APPLY] No change, skipping")
            return
        
        # Застосувати до canvas
        self.canvas.set_label_size(width_mm, height_mm)
        
        # Оновити лінейки
        self.h_ruler.set_length(width_mm)
        self.v_ruler.set_length(height_mm)
        
        logger.info(f"[SIZE-APPLY] Label size updated: {width_mm}x{height_mm}mm")
    
    def _create_units_controls(self):
        """Створити контроли для вибору одиниць вимірювання"""
        # Units ComboBox
        units_label = QLabel("Units:")
        self.units_combobox = QComboBox()
        
        # Додати всі варіанти
        for unit in MeasurementUnit:
            self.units_combobox.addItem(unit.value.upper(), unit)
        
        # Встановити дефолтний
        index = self.units_combobox.findData(self.current_unit)
        self.units_combobox.setCurrentIndex(index)
        
        # Підключити сигнал
        self.units_combobox.currentIndexChanged.connect(self._on_unit_changed)
        
        # Додати до toolbar
        self.toolbar.addSeparator()
        self.toolbar.addWidget(units_label)
        self.toolbar.addWidget(self.units_combobox)
        
        logger.debug(f"[UNITS] Initialized: {self.current_unit.value}")
    
    def _on_unit_changed(self, index):
        """Units ComboBox змінено"""
        old_unit = self.current_unit
        new_unit = self.units_combobox.itemData(index)
        
        logger.info(f"[UNITS] Changed: {old_unit.value} -> {new_unit.value}")
        
        self.current_unit = new_unit
        
        # 1. Оновити Label Size SpinBoxes
        self._update_label_size_spinboxes(old_unit, new_unit)
        
        # 2. Оновити PropertyPanel (якщо є selected element)
        if self.selected_item and hasattr(self.selected_item, 'element'):
            self.property_panel.update_for_unit(new_unit)
        
        # 3. Оновити Rulers
        if hasattr(self.canvas, 'h_ruler') and self.canvas.h_ruler:
            self.canvas.h_ruler.set_unit(new_unit)
        
        if hasattr(self.canvas, 'v_ruler') and self.canvas.v_ruler:
            self.canvas.v_ruler.set_unit(new_unit)
        
        logger.info(f"[UNITS] Update completed")
    
    def _update_label_size_spinboxes(self, old_unit, new_unit):
        """Оновити Label Size SpinBoxes при зміні units"""
        # Отримати поточні значення в MM (завжди зберігаємо в MM!)
        width_mm = UnitConverter.unit_to_mm(
            self.width_spinbox.value(), 
            old_unit
        )
        height_mm = UnitConverter.unit_to_mm(
            self.height_spinbox.value(), 
            old_unit
        )
        
        # Конвертувати в нові units
        width_new = UnitConverter.mm_to_unit(width_mm, new_unit)
        height_new = UnitConverter.mm_to_unit(height_mm, new_unit)
        
        # Оновити SpinBoxes
        from config import CONFIG
        decimals = UNIT_DECIMALS[new_unit]
        step = UNIT_STEPS[new_unit]
        
        # Width
        self.width_spinbox.blockSignals(True)
        self.width_spinbox.setDecimals(decimals)
        self.width_spinbox.setSingleStep(step)
        self.width_spinbox.setSuffix(f" {new_unit.value}")
        
        # Range в нових units
        min_width, max_width = UnitConverter.get_range_in_unit(
            CONFIG['MIN_LABEL_WIDTH_MM'], 
            CONFIG['MAX_LABEL_WIDTH_MM'], 
            new_unit
        )
        self.width_spinbox.setRange(min_width, max_width)
        self.width_spinbox.setValue(width_new)
        self.width_spinbox.blockSignals(False)
        
        # Height (аналогічно)
        self.height_spinbox.blockSignals(True)
        self.height_spinbox.setDecimals(decimals)
        self.height_spinbox.setSingleStep(step)
        self.height_spinbox.setSuffix(f" {new_unit.value}")
        
        min_height, max_height = UnitConverter.get_range_in_unit(
            CONFIG['MIN_LABEL_HEIGHT_MM'], 
            CONFIG['MAX_LABEL_HEIGHT_MM'], 
            new_unit
        )
        self.height_spinbox.setRange(min_height, max_height)
        self.height_spinbox.setValue(height_new)
        self.height_spinbox.blockSignals(False)
        
        logger.debug(f"[UNITS] Label size updated: {width_new:.2f}x{height_new:.2f} {new_unit.value}")
    
    def _toggle_bold(self):
        """Toggle Bold для selected element"""
        if self.selected_item and hasattr(self.selected_item, 'element'):
            element = self.selected_item.element
            
            if hasattr(element, 'bold'):
                element.bold = not element.bold
                
                # Оновити графічний item
                if hasattr(self.selected_item, 'update_display'):
                    self.selected_item.update_display()
                
                # Оновити PropertyPanel checkbox
                if self.property_panel.current_element == element:
                    self.property_panel.bold_checkbox.blockSignals(True)
                    self.property_panel.bold_checkbox.setChecked(element.bold)
                    self.property_panel.bold_checkbox.blockSignals(False)
                
                logger.debug(f"[SHORTCUT] Bold toggled: {element.bold}")
    
    def _toggle_underline(self):
        """Toggle Underline для selected element"""
        if self.selected_item and hasattr(self.selected_item, 'element'):
            element = self.selected_item.element
            
            if hasattr(element, 'underline'):
                element.underline = not element.underline
                
                # Оновити графічний item
                if hasattr(self.selected_item, 'update_display'):
                    self.selected_item.update_display()
                
                # Оновити PropertyPanel checkbox
                if self.property_panel.current_element == element:
                    self.property_panel.underline_checkbox.blockSignals(True)
                    self.property_panel.underline_checkbox.setChecked(element.underline)
                    self.property_panel.underline_checkbox.blockSignals(False)
                
                logger.debug(f"[SHORTCUT] Underline toggled: {element.underline}")
