# НЕДЕЛЯ 2: Онбординг и ранний опыт

## Тема
Путь нового игрока: первая сессия - первая неделя - первая покупка. Как устроен вход в игру и что на него влияет.

## Цели обучения
- Глубоко проанализировать воронку нового игрока
- Провести статистический анализ A/B-тестов (SRM, t-test, chi-square)
- Понять связь между ранним опытом и последующим поведением
- Спроектировать и провести свой эксперимент, направленный на ранний опыт

## Контекст: какие встроенные тесты относятся к теме

| Тест | Что меняет | Ключевые метрики | Trade-off |
|------|-----------|-----------------|-----------|
| `onboarding_length` | Длина туториала (4/8/12 шагов) | D1, D7 retention, tutorial completion | Быстрый старт ↔ глубина понимания механик |
| `starter_pack_price` | Цена стартового пакета ($0.49/$0.99/$1.99) | Конверсия в первую покупку, ARPPU | Конверсия ↔ ARPPU |

Туториал и стартовый пакет — два ключевых момента первых дней жизни игрока. Длина туториала определяет, поймёт ли игрок механики и вернётся ли завтра. Цена стартового пакета определяет, станет ли он платящим. Оба — про то, как сделать вход в игру удачным.

## План блока

### Часть 1: Погружение в тему
- Воронка нового игрока, почему первые 10 минут решают всё
- Ключевые механики раннего опыта в Idle Champions: туториал, первый призыв, стартовый пакет
- Как работают A/B-тесты в данных (поле `ab_tests`), как считать статистику
- Демо: SRM-check на примере одного теста

### Часть 2: Анализ встроенных тестов
- Каждая команда анализирует **оба** теста (`onboarding_length` и `starter_pack_price`)
- Чеклист анализа (см. задание)

### Часть 3: Поиск проблемы и дизайн своего теста 
- Посмотрите на свой дашборд из недели 1
- Ггде отваливаются новички? На каком шаге туториала? На какой главе? Кто не конвертируется?
- Формулируйте гипотезу, проектируйте тест, пишите override-конфиг

### Часть 4: Генерация и начало анализа
- Запуск генератора локально со своим конфигом
- Загрузка данных в свою базу team_XX с run_id
- Анализ результата и графики

## Задание (что сдавать)

### Deliverable: Глава «Ранний опыт игрока» для итогового отчёта

**Часть A — Анализ встроенных тестов:**

Для обоих тестов (`onboarding_length` и `starter_pack_price`):

1. **Проверка корректности сплита:**
   - Размеры групп — равномерно ли распределение?
   - SRM-check (chi-square тест)
   - Нет ли систематических отличий в составе групп?

2. **Метрики по группам:**
   - `onboarding_length`: D1 retention, D7 retention, tutorial completion rate, сессий на D1, время туториала
   - `starter_pack_price`: конверсия в покупку стартового пакета, ARPPU, revenue per user, влияние на повторные покупки

3. **Статистическая значимость:**
   - Доверительные интервалы для разницы
   - p-value (t-test или chi-square)
   - Вывод: значимо ли?

4. **Рекомендация:**
   - `onboarding_length`: какой вариант рекомендуете? D1 vs D7 — что важнее?
   - `starter_pack_price`: что важнее — больше покупателей или выше чек? Посчитать total revenue для каждого варианта
   - Можно ли скомбинировать? (Например: короткий туториал + дешёвый пакет?)

**Часть B — Анализ воронки нового игрока:**
- Воронка: install → tutorial_complete → first_gacha → first_purchase
- На каком шаге туториала люди отваливаются/пропускают?
- Время до первой покупки (дни): распределение
- Отличается ли воронка по платформам (iOS vs Android)? По источникам трафика?

**Часть C — Свой тест на ранний опыт:**

1. **Проблема:** Что вы нашли в данных? Где именно проседает ранний опыт? Для какого сегмента?
2. **Гипотеза:** «Если мы [изменение], то [метрика] изменится на [направление], потому что [логика]»
3. **Дизайн теста:**
   - Варианты (control + treatment)
   - Целевая метрика (D1/D7 retention, конверсия в первую покупку, tutorial completion)
   - Guardrail-метрики (что не должно упасть)
   - Распределение групп
4. **Конфиг:** YAML-файл с вашим тестом
5. **Результаты:** Анализ по чеклисту из части A
6. **Рекомендация:** Раскатывать или нет? Совпало ли с ожиданиями?

**Доп. задание:**
- Сегментация эффекта: различается ли эффект `onboarding_length` для organic vs paid трафика?
- Анализ взаимодействия: `onboarding_length` × `starter_pack_price` — есть ли interaction effect?

## Подсказки и SQL-примеры

### Размеры групп A/B-теста

```sql
SELECT
    JSONExtractString(ab_tests, 'onboarding_length') AS variant,
    uniqExact(user_id) AS users
FROM game_analytics.events
WHERE event_name = 'session_start'
  AND JSONExtractBool(event_properties, 'is_first_session') = true
  AND JSONExtractString(ab_tests, 'onboarding_length') != ''
GROUP BY variant
ORDER BY variant;
```

### Retention по группам теста

```sql
SELECT
    JSONExtractString(ab_tests, 'onboarding_length') AS variant,
    uniqExact(user_id) AS users,
    uniqExactIf(user_id, days_since_install >= 1) AS d1_users,
    uniqExactIf(user_id, days_since_install >= 7) AS d7_users,
    round(d1_users / users * 100, 4) AS d1_retention,
    round(d7_users / users * 100, 4) AS d7_retention
FROM game_analytics.events
WHERE event_name = 'session_start'
  AND JSONExtractString(ab_tests, 'onboarding_length') != ''
GROUP BY variant
ORDER BY variant;
```

### Конверсия и ARPU по группам starter_pack_price

```sql
WITH users AS (
    SELECT DISTINCT
        user_id,
        JSONExtractString(ab_tests, 'starter_pack_price') AS variant
    FROM game_analytics.events
    WHERE JSONExtractString(ab_tests, 'starter_pack_price') != ''
),
purchases AS (
    SELECT
        user_id,
        count() AS purchase_count,
        sum(JSONExtractFloat(event_properties, 'price_usd')) AS total_spent
    FROM game_analytics.events
    WHERE event_name = 'iap_purchase'
    GROUP BY user_id
)
SELECT
    u.variant,
    count() AS total_users,
    countIf(p.user_id != '') AS paying_users,
    round(paying_users / total_users * 100, 4) AS conversion_pct,
    round(sum(coalesce(p.total_spent, 0)) / total_users, 4) AS arpu,
    round(avgIf(p.total_spent, p.user_id != ''), 2) AS arppu,
    sum(coalesce(p.total_spent, 0)) AS total_revenue
FROM users u
LEFT JOIN purchases p ON u.user_id = p.user_id
GROUP BY u.variant
ORDER BY u.variant;
```

### Воронка туториала (по шагам)

```sql
SELECT
    JSONExtractString(event_properties, 'step_name') AS step,
    JSONExtractInt(event_properties, 'step_number') AS step_num,
    uniqExact(user_id) AS users,
    countIf(JSONExtractBool(event_properties, 'is_skipped') = true) AS skipped
FROM game_analytics.events
WHERE event_name = 'tutorial_step'
GROUP BY step, step_num
ORDER BY step_num;
```

### Время до первой покупки

```sql
WITH first_purchase AS (
    SELECT
        user_id,
        min(days_since_install) AS days_to_first_purchase
    FROM game_analytics.events
    WHERE event_name = 'iap_purchase'
    GROUP BY user_id
)
SELECT
    days_to_first_purchase,
    count() AS users
FROM first_purchase
GROUP BY days_to_first_purchase
ORDER BY days_to_first_purchase;
```

### SRM-check в Python

```python
from scipy.stats import chisquare

observed = [16650, 16700, 16650]  # из SQL
expected_ratio = [1/3, 1/3, 1/3]
total = sum(observed)
expected = [total * r for r in expected_ratio]

stat, p_value = chisquare(observed, expected)
print(f"Chi-square: {stat:.4f}, p-value: {p_value:.4f}")
# p > 0.05 → распределение корректно
```

### T-test для сравнения retention

```python
from scipy.stats import ttest_ind
import numpy as np

# is_returned_d7 — массив 0/1 для каждого юзера
t_stat, p_value = ttest_ind(control_d7, treatment_d7)

diff = np.mean(treatment_d7) - np.mean(control_d7)
se = np.sqrt(np.var(control_d7)/len(control_d7) + np.var(treatment_d7)/len(treatment_d7))
ci_lower = diff - 1.96 * se
ci_upper = diff + 1.96 * se
print(f"Diff: {diff:.4f} [{ci_lower:.4f}, {ci_upper:.4f}], p={p_value:.4f}")
```

### Примеры гипотез для своего теста (ранний опыт)

| Проблема | Гипотеза | Что менять в конфиге |
|----------|----------|---------------------|
| Высокий churn на D1 | Награда за возврат на D2 → больше вернутся | `d1_retention_mult` |
| Много пропусков на шагах 5–8 туториала | Сократить до 6 шагов → меньше бросят, рискуем D7 | `d1_retention_mult`, `d7_retention_mult` |
| Низкая конверсия organic-трафика | Показать пакет сразу после первого призыва | `conversion_mult` |
| Высокая конверсия, мало повторных покупок | Второй пакет со скидкой на D3 | `iap_conversion_mult` |

### Как добавить свой тест в конфиг

```yaml
# configs/overrides/my_onboarding_test.yaml
ab_tests:
  my_onboarding_test:
    enabled: true
    variants: ["control", "treatment"]
    weights: [0.50, 0.50]
    activation_condition: null
    effects:
      control: {}
      treatment:
        d1_retention_mult: 1.08
        d7_retention_mult: 1.05
        conversion_mult: 1.15
```

### Генерация и загрузка

```bash
# Генерация (локально)
python generate.py --seed 200 --override configs/overrides/my_onboarding_test.yaml

# Загрузка в свою базу
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --host <VPS> --database team_XX --user team_XX --password team_pass_XX \
    --run-id onboarding_test
```
