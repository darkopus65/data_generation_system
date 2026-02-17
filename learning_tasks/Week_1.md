# Курс: Практикум по аналитике данных в компьютерных играх
## Материалы для 5 недель практики

**Инструменты:** ClickHouse (SQL), Apache Superset (дашборды), Python (генератор, анализ)

**Игра:** Idle Champions: Synthetic — мобильная F2P Idle RPG с gacha-механикой

---


**Процесс занятия:** Изучаем тему → анализируем встроенные тесты → находим проблему → проектируем свои тесты → генерируем данные → анализируем → пишем рекомендации

---

# НЕДЕЛЯ 1: Продукт и метрики здоровья

## Тема
Знакомство с продуктом, данными и инструментами. Построение базовых метрик из сырых событий.

## Цели обучения
- Освоить работу с ClickHouse (SQL по event-based данным)
- Научиться парсить JSON-поля в аналитических запросах
- Понять структуру данных мобильной игры (36 типов событий)
- Построить ключевые метрики продукта из сырых данных
- Научиться строить дашборды в Superset

## План блока (3–4 часа)

### Часть 1: Введение и настройка
- Разбираем что за игра (GDD), какие данные генерируются, как устроен пайплайн
- Подключаемся к ClickHouse (логины team_XX), проверяем доступ
- Знакомство с базой `game_analytics` — эталонный датасет
- Первые запросы: `SELECT count() FROM events`, `SELECT DISTINCT event_name FROM events`

### Часть 2: Исследование данных
- Самостоятельно: исследуйте данные: какие события есть, какие поля, как парсить JSON
- Задание: составить карту данных — какие события для каких метрик пригодятся

### Часть 3: Построение метрик
- Постройте ключевые метрики (см. задание ниже)

### Часть 4: Дашборд
- Подключение Superset к своей базе
- Начало сборки дашборда

## Задание (что сдавать)

### Deliverable: Дашборд здоровья продукта

Дашборд в Superset (или набор SQL-запросов + скриншоты) со следующими метриками:

**Блок 1 — Аудитория:**
- DAU, WAU, MAU — график по дням
- Sticky factor (DAU/MAU)
- Новые установки по дням и по источникам трафика

**Блок 2 — Retention:**
- Retention D1, D7, D30 по когортам (таблица)
- Retention-кривая (день жизни → % вернувшихся)
- Сравнение retention по источникам трафика

**Блок 3 — Монетизация:**
- Revenue по дням
- Конверсия в первую покупку по когортам
- ARPU и ARPPU по дням
- Распределение выручки по продуктам

**Блок 4 — Вовлечённость:**
- Среднее количество сессий на пользователя в день
- Средняя длительность сессии
- Воронка: install → tutorial → gacha → purchase
- Распределение игроков по главам (прогрессия)

**Доп. задание**
- Обнаружить аномалию с плохим трафиком
- Сегментация по платформе (iOS vs Android)

**Важно:** Этот дашборд будет использоваться дальше по неделям. Вы будете опираться на него, чтобы находить проблемы и формулировать гипотезы.

## Подсказки и SQL-примеры

### Подключение к ClickHouse

```
Host: <адрес VPS>
Port: 8123 (HTTP) или 9000 (Native)
Database: game_analytics (read-only эталон) или team_XX (ваша база)
User: team_XX
Password: team_pass_XX
```

Можно подключаться через: DBeaver, DataGrip, clickhouse-client, или SQL Lab в Superset.

### Как парсить JSON-поля

```sql
-- Извлечь строку
JSONExtractString(event_properties, 'install_source')

-- Извлечь число (float)
JSONExtractFloat(event_properties, 'price_usd')

-- Извлечь целое число
JSONExtractInt(event_properties, 'session_duration_sec')

-- Извлечь boolean
JSONExtractBool(event_properties, 'is_first_session')

-- Извлечь группу A/B-теста
JSONExtractString(ab_tests, 'onboarding_length')
```

### DAU

```sql
SELECT
    toDate(event_timestamp) AS date,
    uniqExact(user_id) AS dau
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY date
ORDER BY date;
```

### Retention D1/D7/D30 по когортам

```sql
SELECT
    cohort_date,
    uniqExact(user_id) AS cohort_size,
    uniqExactIf(user_id, days_since_install >= 1) AS returned_d1,
    uniqExactIf(user_id, days_since_install >= 7) AS returned_d7,
    uniqExactIf(user_id, days_since_install >= 30) AS returned_d30,
    round(returned_d1 / cohort_size * 100, 2) AS retention_d1,
    round(returned_d7 / cohort_size * 100, 2) AS retention_d7,
    round(returned_d30 / cohort_size * 100, 2) AS retention_d30
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY cohort_date
ORDER BY cohort_date;
```

### Revenue по дням

```sql
SELECT
    toDate(event_timestamp) AS date,
    count() AS purchases,
    uniqExact(user_id) AS paying_users,
    sum(JSONExtractFloat(event_properties, 'price_usd')) AS revenue
FROM game_analytics.events
WHERE event_name = 'iap_purchase'
GROUP BY date
ORDER BY date;
```

### Воронка конверсии

```sql
WITH user_funnel AS (
    SELECT
        user_id,
        max(event_name = 'session_start') AS step_install,
        max(event_name = 'tutorial_complete') AS step_tutorial,
        max(event_name = 'gacha_summon') AS step_gacha,
        max(event_name = 'iap_purchase') AS step_purchase
    FROM game_analytics.events
    GROUP BY user_id
)
SELECT
    sum(step_install) AS installs,
    sum(step_tutorial) AS tutorial,
    sum(step_gacha) AS gacha,
    sum(step_purchase) AS purchase,
    round(sum(step_tutorial) / sum(step_install) * 100, 1) AS pct_tutorial,
    round(sum(step_gacha) / sum(step_install) * 100, 1) AS pct_gacha,
    round(sum(step_purchase) / sum(step_install) * 100, 1) AS pct_purchase
FROM user_funnel;
```
