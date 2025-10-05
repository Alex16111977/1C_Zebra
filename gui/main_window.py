# -*- coding: utf-8 -*-
"""Главное окно приложения"""

from PySide6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QWidget,
    QGridLayout,
    QMenuBar,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QUndoStack
from .canvas_view import CanvasView
from .toolbar import EditorToolbar
from .sidebar import Sidebar
from .property_panel import PropertyPanel
from .smart_guides import SmartGuides
from .rulers import HorizontalRuler, VerticalRuler
from .mixins import (
    ElementCreationMixin,
    SelectionMixin,
    TemplateMixin,
    ClipboardMixin,
    ShortcutsMixin,
    LabelConfigMixin,
    UIHelpersMixin
)
from core.template_manager import TemplateManager
from zpl.generator import ZPLGenerator
from integration.labelary_client import LabelaryClient
from utils.logger import logger
from utils.unit_converter import MeasurementUnit
from config import DEFAULT_UNIT


class MainWindow(QMainWindow, 
                 ElementCreationMixin,
                 SelectionMixin,
                 TemplateMixin,
                 ClipboardMixin,
                 ShortcutsMixin,
                 LabelConfigMixin,
                 UIHelpersMixin):
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
        
        # Drag state
        self.drag_start_pos = None
        
        # ZPL Generator
        self.zpl_generator = ZPLGenerator(dpi=203)
        self.labelary_client = LabelaryClient(dpi=203)
        self.template_manager = TemplateManager()
        logger.info("ZPL Generator, Labelary Client and Template Manager created")
        
        # Canvas
        self.canvas = CanvasView(width_mm=28, height_mm=28, dpi=203)
        logger.info("Canvas created (28x28mm, DPI 203)")
        
        # Sidebar
        self.sidebar = Sidebar()
        logger.info("Sidebar created")
        
        # Smart Guides
        self.smart_guides = SmartGuides(self.canvas.scene)
        self.guides_enabled = True
        logger.info("Smart Guides initialized")
        
        # Undo/Redo Stack
        self.undo_stack = QUndoStack(self)
        logger.debug(f"[UNDO-STACK] Initialized")
        
        # Rulers
        self.h_ruler = HorizontalRuler(length_mm=28, dpi=203, scale=2.5)
        self.v_ruler = VerticalRuler(length_mm=28, dpi=203, scale=2.5)
        logger.info("Rulers created")
        
        # Link rulers to canvas
        self.canvas.h_ruler = self.h_ruler
        self.canvas.v_ruler = self.v_ruler
        logger.info("Rulers linked to canvas")
        
        # Central widget layout
        central_widget = QWidget()
        grid_layout = QGridLayout(central_widget)
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        corner_spacer = QWidget()
        corner_spacer.setFixedSize(25, 25)
        grid_layout.addWidget(self.sidebar, 0, 0, 2, 1)  # Sidebar ЗЛІВА, spans 2 rows
        grid_layout.addWidget(corner_spacer, 0, 1)
        grid_layout.addWidget(self.h_ruler, 0, 2)
        grid_layout.addWidget(self.v_ruler, 1, 1)
        grid_layout.addWidget(self.canvas, 1, 2)

        self.setCentralWidget(central_widget)
        logger.info("Central widget with rulers configured")

        # Menu bar
        self._create_actions()
        self._create_menus()

        # Toolbar
        self.toolbar = EditorToolbar(self)
        self.addToolBar(self.toolbar)
        logger.info("Toolbar created")
        
        # Property panel
        self.property_panel = PropertyPanel()
        dock = QDockWidget("Properties", self)
        dock.setWidget(self.property_panel)
        dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        logger.info("Property panel created")
        
        # Snap to grid
        self.snap_enabled = True
        
        # Current display unit
        self.current_unit = DEFAULT_UNIT
        
        # Connect signals
        self._connect_signals()
        
        # Setup UI controls from mixins
        self._create_snap_toggle()
        self._create_label_size_controls()
        self._create_units_controls()
        
        # Setup shortcuts
        self._setup_shortcuts()

        logger.info("MainWindow fully initialized")

    def _create_actions(self):
        """Создать QActions для меню"""
        self.new_template_action = QAction("Новый шаблон", self)
        self.new_template_action.setShortcut("Ctrl+N")
        self.new_template_action.triggered.connect(self._create_new_template)

        self.open_template_action = QAction("Открыть...", self)
        self.open_template_action.setShortcut("Ctrl+O")
        self.open_template_action.triggered.connect(self._load_template)

        self.save_template_action = QAction("Сохранить", self)
        self.save_template_action.setShortcut("Ctrl+S")
        self.save_template_action.triggered.connect(self._save_template)

        self.export_zpl_action = QAction("Экспорт ZPL", self)
        self.export_zpl_action.setShortcut("Ctrl+E")
        self.export_zpl_action.triggered.connect(self._export_zpl)

        self.preview_action = QAction("Предпросмотр", self)
        self.preview_action.setShortcut("Ctrl+P")
        self.preview_action.triggered.connect(self._show_preview)

        self.print_action = QAction("Печать...", self)
        self.print_action.setShortcut("Ctrl+Shift+P")
        self.print_action.triggered.connect(self._export_zpl)

        self.undo_action = QAction("Отменить", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._undo)

        self.redo_action = QAction("Повторить", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self._redo)

        self.copy_action = QAction("Копировать", self)
        self.copy_action.setShortcut("Ctrl+C")
        self.copy_action.triggered.connect(self._copy_selected)

        self.paste_action = QAction("Вставить", self)
        self.paste_action.setShortcut("Ctrl+V")
        self.paste_action.triggered.connect(self._paste_from_clipboard)

        self.delete_action = QAction("Удалить", self)
        self.delete_action.setShortcut("Del")
        self.delete_action.triggered.connect(self._delete_selected)

        self.add_text_menu_action = QAction("Текст", self)
        self.add_text_menu_action.setShortcut("Ctrl+T")
        self.add_text_menu_action.triggered.connect(self._add_text)

        self.add_ean13_menu_action = QAction("EAN-13", self)
        self.add_ean13_menu_action.triggered.connect(self._add_ean13)

        self.add_code128_menu_action = QAction("Code 128", self)
        self.add_code128_menu_action.triggered.connect(self._add_code128)

        self.add_qrcode_menu_action = QAction("QR Code", self)
        self.add_qrcode_menu_action.triggered.connect(self._add_qrcode)

        self.add_rectangle_menu_action = QAction("Прямоугольник", self)
        self.add_rectangle_menu_action.triggered.connect(self._add_rectangle)

        self.add_circle_menu_action = QAction("Круг", self)
        self.add_circle_menu_action.triggered.connect(self._add_circle)

        self.add_line_menu_action = QAction("Линия", self)
        self.add_line_menu_action.triggered.connect(self._add_line)

        self.add_image_menu_action = QAction("Изображение", self)
        self.add_image_menu_action.setShortcut("Ctrl+I")
        self.add_image_menu_action.triggered.connect(self._add_image)

        self.guides_toggle_action = QAction("Умные направляющие", self)
        self.guides_toggle_action.setCheckable(True)
        self.guides_toggle_action.setChecked(True)
        self.guides_toggle_action.toggled.connect(
            lambda checked: self._toggle_guides(Qt.Checked if checked else Qt.Unchecked)
        )

        self.grid_toggle_action = QAction("Сетка (Snap)", self)
        self.grid_toggle_action.setCheckable(True)
        self.grid_toggle_action.setChecked(True)
        self.grid_toggle_action.toggled.connect(
            lambda checked: self._toggle_snap(Qt.Checked if checked else Qt.Unchecked)
        )

        self.bring_to_front_action = QAction("На передний план", self)
        self.bring_to_front_action.triggered.connect(self._bring_to_front)

        self.send_to_back_action = QAction("На задний план", self)
        self.send_to_back_action.triggered.connect(self._send_to_back)

        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self._show_about_dialog)

        self.barcode_actions = QActionGroup(self)
        self.barcode_actions.setExclusive(False)
        for action in (
            self.add_ean13_menu_action,
            self.add_code128_menu_action,
            self.add_qrcode_menu_action,
        ):
            self.barcode_actions.addAction(action)

        self.shape_actions = QActionGroup(self)
        self.shape_actions.setExclusive(False)
        for action in (
            self.add_rectangle_menu_action,
            self.add_circle_menu_action,
            self.add_line_menu_action,
        ):
            self.shape_actions.addAction(action)

    def _create_menus(self):
        """Создать меню приложения"""
        menubar: QMenuBar = self.menuBar()
        menubar.clear()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(self.new_template_action)
        file_menu.addSeparator()
        file_menu.addAction(self.open_template_action)
        file_menu.addAction(self.save_template_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_zpl_action)

        edit_menu = menubar.addMenu("Редактирование")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)
        edit_menu.addAction(self.delete_action)

        insert_menu = menubar.addMenu("Вставка")
        insert_menu.addAction(self.add_text_menu_action)

        barcode_menu = QMenu("Штрих-код", self)
        barcode_menu.addAction(self.add_ean13_menu_action)
        barcode_menu.addAction(self.add_code128_menu_action)
        barcode_menu.addAction(self.add_qrcode_menu_action)
        insert_menu.addMenu(barcode_menu)

        shapes_menu = QMenu("Фигуры", self)
        shapes_menu.addAction(self.add_rectangle_menu_action)
        shapes_menu.addAction(self.add_circle_menu_action)
        shapes_menu.addAction(self.add_line_menu_action)
        insert_menu.addMenu(shapes_menu)

        insert_menu.addSeparator()
        insert_menu.addAction(self.add_image_menu_action)

        view_menu = menubar.addMenu("Вид")
        view_menu.addAction(self.guides_toggle_action)
        view_menu.addAction(self.grid_toggle_action)

        arrange_menu = menubar.addMenu("Упорядочить")
        arrange_menu.addAction(self.bring_to_front_action)
        arrange_menu.addAction(self.send_to_back_action)

        tools_menu = menubar.addMenu("Инструменты")
        tools_menu.addAction(self.preview_action)
        tools_menu.addAction(self.print_action)

        help_menu = menubar.addMenu("Справка")
        help_menu.addAction(self.about_action)

    def _create_new_template(self):
        """Создать новый пустой шаблон"""
        logger.info("[MENU] Creating new template")

        self.canvas.clear_and_redraw_grid()
        self.elements.clear()
        self.graphics_items.clear()
        self.undo_stack.clear()
        self.selected_item = None
        self.clipboard_element = None

        self.smart_guides.clear_guides()
        self.h_ruler.clear_highlight()
        self.v_ruler.clear_highlight()
        self.property_panel.set_element(None, None)

        logger.info("[MENU] Canvas reset to blank template")

    def _show_about_dialog(self):
        """Показать окно «О программе»"""
        QMessageBox.about(
            self,
            "О программе",
            "<b>ZPL Label Designer</b><br>"
            "Инструмент для проектирования этикеток ZPL.<br>"
            "© 2024 Zebra Label Tools",
        )

    def _toggle_guides(self, state):
        super()._toggle_guides(state)
        if hasattr(self, "guides_toggle_action"):
            self.guides_toggle_action.blockSignals(True)
            self.guides_toggle_action.setChecked(state == Qt.Checked)
            self.guides_toggle_action.blockSignals(False)

    def _toggle_snap(self, state):
        super()._toggle_snap(state)
        if hasattr(self, "grid_toggle_action"):
            self.grid_toggle_action.blockSignals(True)
            self.grid_toggle_action.setChecked(state == Qt.Checked)
            self.grid_toggle_action.blockSignals(False)

    def _connect_signals(self):
        """Connect all signals"""
        # Canvas signals
        self.canvas.scene.selectionChanged.connect(self._on_selection_changed)
        self.canvas.cursor_position_changed.connect(self._update_ruler_cursor)
        self.canvas.context_menu_requested.connect(self._show_context_menu)
        
        # Event filters
        self.canvas.viewport().installEventFilter(self)
        self.canvas.scene.installEventFilter(self)
        
        # Sidebar signals
        self.sidebar.element_type_selected.connect(self._on_sidebar_element_selected)
        
        # Toolbar signals
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
        
        logger.info("All signals connected")
    
    def _on_sidebar_element_selected(self, element_type: str):
        """
        Обробник вибору елемента з sidebar.
        
        Args:
            element_type: Тип елемента ('text', 'barcode', 'rectangle', etc.)
        """
        logger.debug(f"[SIDEBAR] Element selected: {element_type}")
        
        # Роутинг до відповідного методу створення
        if element_type == 'text':
            self._add_text()
        elif element_type == 'barcode':
            # За замовчуванням додаємо EAN-13
            self._add_ean13()
        elif element_type == 'rectangle':
            self._add_rectangle()
        elif element_type == 'circle':
            self._add_circle()
        elif element_type == 'line':
            self._add_line()
        elif element_type == 'picture':
            self._add_image()
        else:
            logger.warning(f"[SIDEBAR] Unknown element type: {element_type}")
        
        logger.debug(f"[SIDEBAR] Element {element_type} added successfully")
