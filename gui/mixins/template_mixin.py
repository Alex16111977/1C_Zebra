# -*- coding: utf-8 -*-
"""Mixin для template операцій"""

from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QFileDialog, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from io import BytesIO
from datetime import datetime
import json
from pathlib import Path
from utils.logger import logger
from utils.unit_converter import MeasurementUnit
from core.elements.text_element import TextElement, GraphicsTextItem
from core.elements.image_element import ImageElement, GraphicsImageItem
from core.elements.barcode_element import BarcodeElement, GraphicsBarcodeItem


class TemplateMixin:
    """Template save/load and ZPL export operations"""
    
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
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Template",
            str(self.template_manager.templates_dir),
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        try:
            template_data = self.template_manager.load_template(filepath)
            
            # Apply grid config (зворотна сумісність)
            label_config = template_data['label_config']
            if 'grid' in label_config:
                from config import GridConfig, SnapMode
                grid_data = label_config['grid']
                grid_config = GridConfig(
                    size_x_mm=grid_data.get('size_x_mm', 1.0),
                    size_y_mm=grid_data.get('size_y_mm', 1.0),
                    offset_x_mm=grid_data.get('offset_x_mm', 0.0),
                    offset_y_mm=grid_data.get('offset_y_mm', 0.0),
                    visible=grid_data.get('visible', True),
                    snap_mode=SnapMode(grid_data.get('snap_mode', 'grid'))
                )
                self.canvas.set_grid_config(grid_config)
                logger.debug(f"[TEMPLATE-LOAD] Loaded grid: Size X={grid_config.size_x_mm}mm, Offset Y={grid_config.offset_y_mm}mm")
            else:
                # Старі template без grid - defaults
                logger.debug("[TEMPLATE-LOAD] No grid config - using defaults")
                from config import GridConfig
                self.canvas.set_grid_config(GridConfig())
            
            self.canvas.clear_and_redraw_grid()
            self.elements.clear()
            self.graphics_items.clear()
            
            display_unit = template_data.get('display_unit', MeasurementUnit.MM)
            
            index = self.units_combobox.findData(display_unit)
            if index >= 0:
                self.units_combobox.setCurrentIndex(index)
            
            logger.info(f"[TEMPLATE] Applied display_unit: {display_unit.value}")
            
            label_config = template_data['label_config']
            width_mm = label_config.get('width_mm', 28)
            height_mm = label_config.get('height_mm', 28)
            
            logger.debug(f"[LOAD-TEMPLATE] Label size from template: {width_mm}x{height_mm}mm")
            
            if width_mm != self.canvas.width_mm or height_mm != self.canvas.height_mm:
                logger.info(f"[LOAD-TEMPLATE] Applying new label size: {width_mm}x{height_mm}mm")
                self.canvas.set_label_size(width_mm, height_mm)

                self.width_spinbox.blockSignals(True)
                self.height_spinbox.blockSignals(True)
                self.width_spinbox.setValue(width_mm)
                self.height_spinbox.setValue(height_mm)
                self.width_spinbox.blockSignals(False)
                self.height_spinbox.blockSignals(False)
                
                logger.debug(f"[LOAD-TEMPLATE] Spinboxes updated: W={width_mm}, H={height_mm}")
            
            for element in template_data['elements']:
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
