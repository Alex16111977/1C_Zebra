# -*- coding: utf-8 -*-
"""Mixin для clipboard операцій"""

from utils.logger import logger
import copy


class ClipboardMixin:
    """Copy/paste/duplicate/move operations"""
    
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
