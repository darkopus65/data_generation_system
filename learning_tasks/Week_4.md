# НЕДЕЛЯ 4: Трафик, LTV и бизнес-планирование

## Тема
Откуда приходят игроки, сколько они стоят, сколько приносят и сколько принесут. Качество трафика, фрод, когортная финмодель, сценарное планирование. Сборка итогового отчёта.

## Цели обучения
- Анализировать качество трафика по каналам
- Обнаруживать фродовый/некачественный трафик
- Строить когортную финансовую модель (LTV, CAC, ROI)
- Моделировать сценарии «что если…» через генерацию данных с разными конфигами
- Собрать итоговый отчёт и защитить перед «стейкхолдерами»

## Контекст

| Данные | Что анализируем |
|--------|----------------|
| Встроенный тест `late_game_offer` | Офферы для ветеранов (D30+) — влияние на LTV и долгосрочный retention |
| Сценарий `bad_traffic` | Фрод-трафик на день ~25 — как обнаружить и оценить ущерб |
| Источники трафика | CAC, retention, LTV по каналам |

**Почему `late_game_offer` здесь:** тест про D30+ игроков — ветеранов. Его эффект проявляется в LTV и долгосрочном retention. Это вопрос «сколько игрок приносит за жизнь и как это увеличить» — идеально для финмоделирования.

## План блока

### Часть 1: Погружение в тему
- Unit-экономика мобильных игр, CAC/LTV/ROI
- Как определять качество трафика: retention по каналам, паттерны ботов
- Когортный LTV: зачем и как экстраполировать

### Часть 2: Анализ трафика и late_game_offer
- Анализ `late_game_offer`: офферы для ветеранов и LTV
- Обнаружение фрода: аномалия на день ~25, характеристики fake_network
- Качество каналов: retention и монетизация по source

### Часть 3: Финансовая модель + сценарии
- Когортный LTV: retention-кривая → экстраполяция → cumulative LTV
- CAC по каналам, ROI
- Сценарный анализ: генерация 2 сценариев с разными конфигами, сравнение через run_id

### Часть 4: Сборка итогового отчёта
- Единая картина из наработок
- Executive Summary и приоритезированный план действий
- Презентацию для защиты


## Задание (что сдавать)

### Deliverable A: Глава «Трафик и бизнес-планирование»

**Часть A — Анализ `late_game_offer`:**

1. **Проверка сплита:** SRM-check (тест активируется на day 30+ — выборка меньше!)
2. **Метрики:** конверсия в IAP среди D30+ игроков, D30–D60 retention, revenue per user для D30+
3. **Статистика:** CI, p-value. Хватает ли выборки? Если нет — обсудить power analysis.
4. **Рекомендация:** discount_50 vs bonus_hero — у них разные эффекты. Что лучше для LTV?

**Часть B — Анализ трафика:**

1. **Обнаружение фрода:**
   - Найти аномалию на ~день 25 (всплеск установок из `fake_network`)
   - Характеристики фрод-трафика: retention, сессии, монетизация vs нормальный трафик
   - Оценка: сколько установок — боты? Как определили?
   - Оценка ущерба: сколько стоил бы этот трафик при оплате?

2. **Качество каналов:**
   - Retention по каждому каналу (organic, google_ads, facebook, unity_ads, influencer, cross_promo)
   - Монетизация по каналам (конверсия, ARPU)
   - Ранжирование каналов по качеству

**Часть C — Когортная финансовая модель:**

1. **Retention-прогноз:** кривая retention по дням жизни, экстраполяция на D60, D90
2. **LTV по когортам:** cumulative revenue / cohort_size, LTV D30, LTV D60 (прогнозный)
3. **Unit-экономика по каналам:**
   - CAC: бенчмарки (organic = $0, google_ads = $2, facebook = $1.5, unity_ads = $1, influencer = $3, cross_promo = $0.5) или обоснуйте свои
   - ROI = LTV / CAC по каналам
   - Какие каналы прибыльны? Куда увеличить/сократить UA-бюджет?
4. **Прогноз revenue:** на основе когорт + ожидаемых установок

**Часть D — Сценарный анализ:**

Сгенерировать минимум 2 сценария помимо baseline:
- «Увеличили бюджет на плохой канал» → больше bad_traffic
- «Больше китов» → high_whale_ratio override
- «Агрессивная монетизация» → повысить цены, сократить бесплатные gems
- «Органический рост» → больше organic, меньше paid
- Свой вариант, связанный с выводами предыдущих недель

Для каждого сценария:
- Что изменили (приложить YAML) и зачем
- Сравнение метрик через run_id (таблица: run_id × метрика)
- Влияние на LTV и unit-экономику
- Вывод: стоит ли применять стратегию?

**Доп. задание:**
- Monte Carlo: диапазон прогнозного revenue при разных предположениях
- Sensitivity analysis: насколько LTV чувствителен к изменению retention на 1 п.п.?
- Свой тест на LTV / ветеранов (дополнительно к сценариям)

### Deliverable B: Итоговый отчёт + защита

**Итоговый отчёт** — презентация и отчет:

План презентации:
1. **Executive Summary:** три главных проблемы, три рекомендации, ожидаемый эффект в цифрах
2. **Состояние продукта:** ключевые метрики, тренды, дашборд
3. **Анализ AB тестов:** разбор нескольких тестов с результатами
4. **Монетизация и финансы:** состояния финансовой части продукта
5. **Приоритезированный план действий на квартал:** что внедрить первым? Какие ожидаемые эффекты?
6. **Дополнительные интересные выводы:** все что нашли из интересного

**Защита:** 6–8 минут презентация + 5 минут вопросы.

Отчет: сдается дополниенением к презентации с полными результатами выполнения заданий и аналитики всех недель. Формат: pdf или питон тетрадка. Обязательно вкючить:
1. Скриншоты всех графиков к описаниям и выводам
2. Расчеты статистик и основных наиболее интересных SQL запросов 
3. Конфиги и параметры, которые в итоге применяли для новых генераций

## Подсказки и SQL-примеры

### Анализ late_game_offer (только D30+ игроки)

```sql
WITH d30_users AS (
    SELECT DISTINCT
        user_id,
        JSONExtractString(ab_tests, 'late_game_offer') AS variant
    FROM game_analytics.events
    WHERE days_since_install >= 30
      AND JSONExtractString(ab_tests, 'late_game_offer') != ''
)
SELECT
    variant,
    count() AS users,
    countIf(user_id IN (
        SELECT user_id FROM game_analytics.events
        WHERE event_name = 'iap_purchase' AND days_since_install >= 30
    )) AS d30_payers,
    round(d30_payers / users * 100, 2) AS d30_conversion
FROM d30_users
GROUP BY variant
ORDER BY variant;
```

### Детекция аномалии трафика

```sql
SELECT
    cohort_date,
    JSONExtractString(event_properties, 'install_source') AS source,
    uniqExact(user_id) AS installs
FROM game_analytics.events
WHERE event_name = 'session_start'
  AND JSONExtractBool(event_properties, 'is_first_session') = true
GROUP BY cohort_date, source
ORDER BY cohort_date, source;
```

### Характеристики фрод-трафика

```sql
WITH user_source AS (
    SELECT
        user_id,
        JSONExtractString(event_properties, 'install_source') AS source
    FROM game_analytics.events
    WHERE event_name = 'session_start'
      AND JSONExtractBool(event_properties, 'is_first_session') = true
)
SELECT
    us.source,
    count(DISTINCT us.user_id) AS users,
    round(uniqExactIf(e.user_id, e.days_since_install >= 1) /
          count(DISTINCT us.user_id) * 100, 2) AS d1_ret,
    round(uniqExactIf(e.user_id, e.days_since_install >= 7) /
          count(DISTINCT us.user_id) * 100, 2) AS d7_ret,
    round(avg(JSONExtractInt(e.event_properties, 'session_duration_sec')), 0) AS avg_session_sec
FROM user_source us
JOIN game_analytics.events e ON us.user_id = e.user_id AND e.event_name = 'session_end'
GROUP BY us.source
ORDER BY users DESC;
```

### LTV по когортам (кумулятивный)

```sql
WITH daily_revenue AS (
    SELECT
        cohort_date,
        days_since_install,
        sum(JSONExtractFloat(event_properties, 'price_usd')) AS revenue
    FROM events
    WHERE event_name = 'iap_purchase' AND run_id = 'baseline'
    GROUP BY cohort_date, days_since_install
),
cohort_sizes AS (
    SELECT cohort_date, uniqExact(user_id) AS cohort_size
    FROM events
    WHERE event_name = 'session_start'
      AND JSONExtractBool(event_properties, 'is_first_session') = true
      AND run_id = 'baseline'
    GROUP BY cohort_date
)
SELECT
    dr.cohort_date,
    dr.days_since_install,
    cs.cohort_size,
    sum(dr.revenue) OVER (PARTITION BY dr.cohort_date ORDER BY dr.days_since_install) AS cum_revenue,
    round(cum_revenue / cs.cohort_size, 4) AS ltv
FROM daily_revenue dr
JOIN cohort_sizes cs ON dr.cohort_date = cs.cohort_date
ORDER BY dr.cohort_date, dr.days_since_install;
```

### Сравнение сценариев через run_id

```sql
SELECT
    run_id,
    uniqExact(user_id) AS total_users,
    uniqExactIf(user_id, event_name = 'iap_purchase') AS paying_users,
    round(paying_users / total_users * 100, 2) AS conversion_pct,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') AS revenue,
    round(revenue / total_users, 4) AS arpu
FROM events  -- ваша база team_XX
GROUP BY run_id
ORDER BY run_id;
```

### Экстраполяция retention в Python

```python
import numpy as np
from scipy.optimize import curve_fit

def power_law(t, a, b):
    return a * np.power(t, -b)

# days и retention_pct из SQL (начиная с D1)
popt, _ = curve_fit(power_law, days[1:], retention[1:], p0=[40, 0.5])

for d in [60, 90, 180]:
    print(f"D{d} retention: {power_law(d, *popt):.2f}%")
```

### Бенчмарки CAC по каналам

| Канал | CAC | Обоснование |
|-------|-----|-------------|
| organic | $0 | Бесплатный трафик |
| google_ads | $2.00 | Средний CPI gaming |
| facebook | $1.50 | Средний CPI gaming |
| unity_ads | $1.00 | Cross-promo сети |
| influencer | $3.00 | Дорогой, но целевой |
| cross_promo | $0.50 | Внутренние каналы |
| fake_network | $0.80 | Дешёвый = подозрительный |

---