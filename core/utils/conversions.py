# -*- coding: utf-8 -*-
"""Допоміжні конвертації одиниць для ZPL"""

from utils.logger import logger


def points_to_dots(points: float, dpi: int = 203) -> int:
    """Конвертація points → dots"""
    dots = int(round(points * dpi / 72))
    logger.debug(f"[CONVERT] {points}pt -> {dots} dots @ {dpi}DPI")
    return max(dots, 0)


def dots_to_points(dots: int, dpi: int = 203) -> float:
    """Конвертація dots → points"""
    points = dots * 72 / dpi
    logger.debug(f"[CONVERT] {dots} dots -> {points:.2f}pt @ {dpi}DPI")
    return max(points, 0.0)


def mm_to_dots(mm: float, dpi: int = 203) -> int:
    """Конвертація мм → dots"""
    dots = int(round(mm * dpi / 25.4))
    logger.debug(f"[CONVERT] {mm}mm -> {dots} dots @ {dpi}DPI")
    return max(dots, 0)


def dots_to_mm(dots: int, dpi: int = 203) -> float:
    """Конвертація dots → мм"""
    mm = dots * 25.4 / dpi
    logger.debug(f"[CONVERT] {dots} dots -> {mm:.2f}mm @ {dpi}DPI")
    return max(mm, 0.0)
