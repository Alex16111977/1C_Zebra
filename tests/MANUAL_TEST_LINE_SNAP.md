# 🧪 MANUAL TEST: Line Snap to Grid - Both Ends

## ✅ ЧТО ПРОВЕРЯЕМ

Line элемент теперь snap'ит **ОБА конца** к сетке при drag:
- Start point (x, y) → snap к grid
- End point (x2, y2) → snap к grid

---

## 🚀 КАК ЗАПУСТИТЬ

1. **Открой командную строку:**
   ```
   cd D:\AiKlientBank\1C_Zebra
   ```

2. **Активируй venv:**
   ```
   .venv\Scripts\activate
   ```

3. **Запусти GUI:**
   ```
   python main.py
   ```

---

## 📋 ТЕСТ-КЕЙСЫ

### TEST 1: Создать Line и проверить snap

1. **Добавить Line:**
   - Sidebar → кнопка "Line" (или Menu → Add → Line)
   - Line появится на canvas

2. **Проверить начальные координаты:**
   - Выбери Line (кликни на неё)
   - Property Panel → посмотри:
     - Position X, Y (start point)
     - End X, End Y (end point)

3. **Drag Line:**
   - Зажми Line и перемести на canvas
   - **ОЖИДАНИЕ:** При drag оба конца должны "прилипать" к grid линиям

4. **Проверить финальные координаты:**
   - Property Panel должен показать:
     - Position X = кратно 1mm (например: 10.0, 11.0, 12.0)
     - Position Y = кратно 1mm
     - End X = кратно 1mm
     - End Y = кратно 1mm

### TEST 2: Проверить что snap работает для ОБОИХ концов

1. **Создать Line с "неровными" координатами:**
   - Property Panel → вручную введи:
     - Position X = 9.55mm
     - Position Y = 9.67mm
     - End X = 24.89mm
     - End Y = 10.23mm

2. **Drag немного (1-2px):**
   - Сдвинь Line на 1-2 пикселя

3. **Проверить результат:**
   - **Start point** должен snap'нуться: 9.55 → 10.0mm, 9.67 → 10.0mm
   - **End point** должен snap'нуться: 24.89 → 25.0mm, 10.23 → 10.0mm
   - Property Panel должен показать координаты кратные 1mm

### TEST 3: Toggle Snap On/Off

1. **Выключить Snap:**
   - Toolbar → checkbox "Snap to Grid" → uncheck
   - ИЛИ нажми Ctrl+G

2. **Drag Line:**
   - Line должна перемещаться БЕЗ snap
   - Координаты могут быть дробными (например: 9.68mm, 10.34mm)

3. **Включить Snap:**
   - Toolbar → checkbox "Snap to Grid" → check
   - ИЛИ нажми Ctrl+G снова

4. **Drag Line:**
   - Line должна snap'иться к grid линиям
   - Координаты кратные 1mm

---

## ✅ КРИТЕРИИ УСПЕХА

### ✓ PASS если:
- ✅ Start point (x, y) snap'ится к grid при drag
- ✅ **End point (x2, y2) snap'ится к grid при drag** ← ГЛАВНОЕ!
- ✅ Property Panel показывает координаты кратные 1mm (10.0, 11.0, 25.0...)
- ✅ Snap toggle работает (On/Off)
- ✅ Line визуально "прилипает" к grid линиям

### ❌ FAIL если:
- ❌ End point НЕ snap'ится (остается дробным: 24.89mm)
- ❌ Только start point snap'ится, end "плавает"
- ❌ Property Panel показывает дробные координаты после snap

---

## 🐛 ЧТО ДЕЛАТЬ ЕСЛИ FAIL

1. **Проверь логи:**
   ```
   type logs\zpl_designer.log | findstr /I "LINE-SNAP"
   ```
   
   Должны быть:
   ```
   [LINE-SNAP] Start: (...) -> (...) mm
   [LINE-SNAP] End: (...) -> (...) mm
   ```

2. **Если End snap логов НЕТ:**
   - Значит snap НЕ работает для end point
   - Проверь что изменения применились в shape_element.py

3. **Сообщи результат:**
   - PASS или FAIL?
   - Скриншот Property Panel после drag
   - Последние 50 строк из логов

---

## 📸 СКРИНШОТ ДЛЯ ОТЧЕТА

Сделай скриншот где видно:
1. Canvas с Line элементом
2. Property Panel с координатами
3. Toolbar с "Snap to Grid" checkbox (checked)

**Координаты должны быть кратными 1mm!**

---

## 🎯 ГОТОВО?

После тестирования:
- [ ] Line snap работает для обоих концов
- [ ] Property Panel показывает правильные координаты
- [ ] Snap toggle работает
- [ ] Нет багов в GUI

**Можно переключить логи на NORMAL:**
```
config.py → CURRENT_LOG_LEVEL = 'NORMAL'
```

---

**ТЕСТ СОЗДАН:** 2025-10-06
**BUG FIX:** Line snap для обоих концов
**EXIT CODE:** 0 (automated test passed)
