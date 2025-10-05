# Швидка шпаргалка: Рівні логування

## Як працювати з логуванням при розробці

### 1️⃣ Розробка нової фічі
```python
# config.py
CURRENT_LOG_LEVEL = 'DEBUG'    # Для GUI компонентів (Canvas, Rulers)
# АБО
CURRENT_LOG_LEVEL = 'VERBOSE'  # Для глибокого аналізу всіх деталей
```

**Запусти додаток → дивись деталі в консолі та logs/app.log**

### 2️⃣ Тестування через логи
- Бачиш кожен крок роботи фічі
- Перевіряєш координати, події, конвертації
- Знаходиш баги швидше

### 3️⃣ Фіча працює? Вимкни деталізацію
```python
# config.py
CURRENT_LOG_LEVEL = 'NORMAL'   # Тільки важлива інформація
```

### 4️⃣ Production (релізна версія)
```python
# config.py
CURRENT_LOG_LEVEL = 'MINIMAL'  # Тільки критичні помилки
```

## Швидке перемикання

| Рівень | Коли використовувати | Що логується |
|--------|---------------------|--------------|
| **VERBOSE** | Глибока відладка | ВСЕ включно з елементами |
| **DEBUG** | Розробка GUI | Canvas, Rulers, координати |
| **NORMAL** | Повсякденна робота | ZPL, API, Templates |
| **MINIMAL** | Production | Тільки помилки |

## Приклад робочого циклу

```python
# 1. Почав робити нову фічу "Add Image Element"
CURRENT_LOG_LEVEL = 'DEBUG'

# 2. Баг з координатами? Збільшую деталізацію
CURRENT_LOG_LEVEL = 'VERBOSE'

# 3. Виправив, протестував - працює!
CURRENT_LOG_LEVEL = 'NORMAL'

# 4. Готую до релізу
CURRENT_LOG_LEVEL = 'MINIMAL'
```

## Категорії (можна вимикати окремо в config.py)

```python
LOG_CATEGORIES = {
    'canvas': True,    # Події Canvas
    'rulers': True,    # Лінійки та cursor
    'elements': True,  # Елементи (тільки VERBOSE)
    'zpl': True,       # ZPL генерація (завжди)
    'api': True,       # API запити (завжди)
    'template': True   # Шаблони (завжди)
}
```

## 💡 Золоте правило

**Тестуєш = DEBUG/VERBOSE**  
**Працює = NORMAL**  
**Релізиш = MINIMAL**

Одна змінна в config.py керує всім логуванням!
