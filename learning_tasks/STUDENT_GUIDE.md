# Песочница: Idle Champions Analytics
## Инструкция для студентов

---

## 1. Что это за проект

Вы работаете с **синтетическими данными мобильной F2P-игры** Idle Champions (жанр: Idle RPG + Gacha). Данные сгенерированы имитационной моделью, которая симулирует поведение ~50,000 игроков за 90 дней.

Данные реалистичны: retention, конверсия, whale/dolphin/F2P поведение, A/B-тесты, аномалии трафика — всё как в настоящей мобильной игре.

**Ваш рабочий процесс:**

```
                    ┌─────────────────┐
                    │  Изучить GDD    │ ← Понять, что за игра
                    └────────┬────────┘
                             ▼
┌─────────────┐     ┌────────────────┐     ┌──────────────┐
│ Генератор   │────▶│  ClickHouse    │◀────│  Superset    │
│ (локально)  │     │  (на сервере)  │     │  (дашборды)  │
└─────────────┘     └────────────────┘     └──────────────┘
  Генерируете         Храните и              Визуализируете
  данные              анализируете           результаты
                      через SQL
```

---

## 2. Что где лежит в проекте

```
проект/
├── generate.py              ← Запуск генератора (точка входа)
├── requirements.txt         ← Зависимости Python
│
├── configs/
│   ├── default.yaml         ← ВСЕ параметры игры и симуляции (главный конфиг)
│   └── overrides/           ← Готовые сценарии (можно создавать свои)
│       └── small_test.yaml  ← Маленький датасет для быстрого тестирования
│
├── src/                     ← Код генератора (не нужно менять)
│
├── scripts/
│   └── load_to_clickhouse.py ← Загрузка данных на сервер
│
├── docs/
│   ├── GDD_v0.2.md          ← Описание игры (механики, валюты, герои)
│   └── gen/
│       ├── EVENTS_REFERENCE.md  ← Справочник 36 типов событий ← ВАЖНО
│       ├── AB_TESTS.md          ← Описание 6 встроенных A/B-тестов
│       └── CONFIGURATION.md     ← Все параметры конфигурации
│
└── output/                  ← Сюда попадают сгенерированные данные
```

**Что прочитать в первую очередь:**
1. `docs/GDD_v0.2.md` — чтобы понять, что за игра
2. `docs/gen/EVENTS_REFERENCE.md` — чтобы понять, какие данные есть
3. Эту инструкцию — чтобы понять, как всем пользоваться

---

## 3. Доступы

### ClickHouse (хранилище данных)

| Параметр | Значение |
|----------|----------|
| Адрес | `<АДРЕС_VPS>` |
| HTTP-порт | `8123` |
| Native-порт | `9000` |
| Ваша база (чтение/запись) | `team_XX` |
| Эталонная база (только чтение) | `game_analytics` |
| Логин | `team_XX` |
| Пароль | `team_pass_XX` |

**Эталонная база `game_analytics`** — общий датасет для всех команд (read-only). Используйте его для первых заданий.

**Ваша база `team_XX`** — сюда вы загружаете свои данные. Полные права.

### Superset (визуализация)

| Параметр | Значение |
|----------|----------|
| URL | `http://<АДРЕС_VPS>:8088` |
| Логин | `team_XX` |
| Пароль | `team_pass_XX` |

### Как подключиться к ClickHouse из разных инструментов

**DBeaver (рекомендуется):**
1. Создать подключение → ClickHouse
2. Host: `<АДРЕС_VPS>`, Port: `8123`
3. Database: `game_analytics` (или `team_XX`)
4. User: `team_XX`, Password: `team_pass_XX`

**DataGrip:**
1. New → Data Source → ClickHouse
2. Те же параметры, что выше

**clickhouse-client (командная строка):**
```bash
clickhouse-client --host <АДРЕС_VPS> --port 9000 \
    --user team_XX --password team_pass_XX \
    --database game_analytics
```

**SQL Lab в Superset:**
1. Открыть Superset → SQL → SQL Лаборатория
2. Выбрать подключённую базу слева
3. Писать SQL прямо в браузере

---

## 4. Работа с эталонным датасетом (недели 1–2)

На первых неделях вы работаете с общей базой `game_analytics`. Данные уже загружены, ничего генерировать не нужно.

### Структура данных

В базе одна основная таблица — `events`. Это сырые события, как в реальном аналитическом пайплайне. Все 36 типов событий лежат в одной таблице.

**Основные колонки:**

| Колонка | Тип | Описание |
|---------|-----|----------|
| `run_id` | String | Идентификатор прогона (для ваших данных) |
| `event_name` | String | Тип события (`session_start`, `iap_purchase`, ...) |
| `event_timestamp` | DateTime | Время события |
| `user_id` | String | ID пользователя |
| `session_id` | String | ID сессии |
| `platform` | String | `ios` / `android` |
| `country` | String | Страна (RU, US, DE, ...) |
| `player_level` | UInt16 | Уровень игрока на момент события |
| `vip_level` | UInt8 | VIP-уровень |
| `total_spent_usd` | Float32 | Суммарные траты в USD на момент события |
| `days_since_install` | UInt16 | Сколько дней прошло с установки |
| `cohort_date` | Date | Дата установки (когорта) |
| `ab_tests` | String | JSON с A/B-группами пользователя |
| `event_properties` | String | JSON со свойствами события |

**Два JSON-поля** `ab_tests` и `event_properties` содержат дополнительные данные, разные для каждого типа события. Чтобы достать из них значения:

```sql
-- Строка
JSONExtractString(event_properties, 'install_source')

-- Число
JSONExtractFloat(event_properties, 'price_usd')
JSONExtractInt(event_properties, 'session_duration_sec')

-- Boolean
JSONExtractBool(event_properties, 'is_first_session')

-- A/B-группа
JSONExtractString(ab_tests, 'onboarding_length')
```

### Первые запросы для проверки

```sql
-- Сколько всего событий
SELECT count() FROM game_analytics.events;

-- Какие типы событий есть
SELECT event_name, count() AS cnt
FROM game_analytics.events
GROUP BY event_name
ORDER BY cnt DESC;

-- Сколько уникальных пользователей
SELECT uniqExact(user_id) FROM game_analytics.events;

-- Посмотреть одно событие целиком
SELECT * FROM game_analytics.events LIMIT 1 FORMAT Vertical;
```

### Ключевые типы событий

| Событие | Что содержит | Для чего нужно |
|---------|-------------|---------------|
| `session_start` | install_source, is_first_session, session_number | DAU, retention, когорты, источники трафика |
| `session_end` | session_duration_sec, events_count | Длительность сессий, вовлечённость |
| `iap_purchase` | product_id, price_usd, currency_amount | Revenue, конверсия, ARPU |
| `gacha_summon` | banner_type, result_rarity, pity_counter, gems_spent | Анализ гачи, pity system |
| `stage_complete` | chapter, stage, result, duration_sec | Прогрессия, воронка |
| `stage_failed` | chapter, stage, fail_reason | Где застревают игроки |
| `tutorial_complete` | steps_completed, duration_sec | Онбординг |
| `ad_completed` | placement, reward_currency, reward_amount | Ad revenue |
| `ad_skipped` | placement, skip_reason | Отказ от рекламы |
| `economy_source` | currency, amount, source | Откуда приходит валюта |
| `economy_sink` | currency, amount, sink | Куда тратится валюта |
| `daily_login` | consecutive_days, reward_currency | Активность |

Полный справочник: `docs/gen/EVENTS_REFERENCE.md`

---

## 5. Генерация своих данных (начиная с недели 2)

Когда вам нужно провести свой эксперимент — вы запускаете генератор локально, а потом загружаете результат на сервер.

### Шаг 1: Установка (один раз)

```bash
# Клонировать/скачать проект
cd путь/к/проекту

# Установить зависимости
pip install -r requirements.txt
```

**Требования:** Python 3.10+, ~4 GB RAM для полной генерации.

### Шаг 2: Тестовый запуск

Прежде чем генерировать полный датасет, убедитесь что всё работает:

```bash
python generate.py --seed 42 --override configs/overrides/small_test.yaml
```

Это создаст маленький датасет (500 юзеров, 7 дней) за несколько секунд. Результат появится в `output/run_YYYYMMDD_HHMMSS/`.

### Шаг 3: Генерация рабочего датасета

Для нормального анализа рекомендуется:

```bash
python generate.py --seed 42
```

Это ~50,000 юзеров, 90 дней, 20–40M событий. Займёт 3–10 минут.

**Для ускорения** можно создать свой override с меньшим объёмом:

```yaml
# configs/overrides/medium.yaml
simulation:
  duration_days: 45

installs:
  total: 15000
```

```bash
python generate.py --seed 42 --override configs/overrides/medium.yaml
```

Это ~15,000 юзеров, 45 дней — достаточно для анализа, генерируется за 1–3 минуты.

### Шаг 4: Создание своего эксперимента

Чтобы добавить свой A/B-тест или изменить параметры — создайте override-файл:

```yaml
# configs/overrides/my_experiment.yaml

# Можно уменьшить объём для скорости
simulation:
  duration_days: 45

installs:
  total: 15000

# Добавить свой A/B-тест
ab_tests:
  my_retention_test:
    enabled: true
    variants: ["control", "treatment_a", "treatment_b"]
    weights: [0.33, 0.33, 0.34]
    activation_condition: null
    effects:
      control: {}
      treatment_a:
        d7_retention_mult: 1.10     # +10% к D7 retention
        sessions_mult: 1.05         # +5% сессий в день
      treatment_b:
        d7_retention_mult: 1.15     # +15% к D7 retention
        conversion_mult: 0.95       # -5% конверсия (trade-off)
```

Запуск:

```bash
python generate.py --seed 100 --override configs/overrides/my_experiment.yaml
```

**Важно:** используйте другой `--seed` для каждого эксперимента, иначе получите те же данные.

### Доступные модификаторы для A/B-тестов

| Модификатор | Что меняет | Пример |
|-------------|-----------|--------|
| `d1_retention_mult` | Вероятность возврата на D1 | `1.05` = +5% |
| `d7_retention_mult` | Вероятность возврата на D7 | `0.90` = -10% |
| `d30_d60_retention_mult` | Retention D30–D60 | `1.10` = +10% |
| `sessions_mult` | Количество сессий в день | `1.20` = +20% |
| `conversion_mult` | Общая конверсия в покупку | `0.85` = -15% |
| `iap_conversion_mult` | Вероятность IAP | `1.25` = +25% |
| `energy_purchase_mult` | Покупки энергии | `0.70` = -30% |
| `ad_watch_mult` | Просмотры рекламы | `1.40` = +40% |
| `gacha_desire_mult` | Желание делать призывы | `1.15` = +15% |

Значения: `1.0` = без изменений, `>1.0` = увеличение, `<1.0` = уменьшение.

Полная документация: `docs/gen/CONFIGURATION.md`

---

## 6. Загрузка данных в ClickHouse

После генерации нужно загрузить данные на сервер в вашу базу.

### Загрузка нового прогона

```bash
python scripts/load_to_clickhouse.py \
    --input output/run_YYYYMMDD_HHMMSS/events.jsonl.gz \
    --host <АДРЕС_VPS> \
    --database team_XX \
    --user team_XX \
    --password team_pass_XX \
    --run-id baseline
```

**Параметры:**
- `--input` — путь к файлу с данными (подставьте актуальное имя папки из `output/`)
- `--host` — адрес сервера
- `--database` — ваша база (`team_01`, `team_02`, ...)
- `--run-id` — **обязательно**, уникальное имя для этого прогона

### Загрузка второго прогона (эксперимент)

```bash
python scripts/load_to_clickhouse.py \
    --input output/run_YYYYMMDD_HHMMSS/events.jsonl.gz \
    --host <АДРЕС_VPS> \
    --database team_XX \
    --user team_XX \
    --password team_pass_XX \
    --run-id my_experiment
```

Теперь в вашей базе два набора данных. Можно сравнивать:

```sql
-- Какие прогоны загружены
SELECT run_id, uniqExact(user_id) AS users, count() AS events
FROM team_XX.events
GROUP BY run_id;

-- Сравнить метрики между прогонами
SELECT
    run_id,
    uniqExactIf(user_id, event_name = 'iap_purchase') AS paying_users,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') AS revenue
FROM team_XX.events
GROUP BY run_id;
```

### Удаление прогона

Если прогон больше не нужен или загрузили неправильные данные:

```bash
python scripts/load_to_clickhouse.py \
    --delete-run my_experiment \
    --host <АДРЕС_VPS> \
    --database team_XX \
    --user team_XX \
    --password team_pass_XX
```

---

## 7. Работа в Superset

Superset — это BI-инструмент для построения графиков и дашбордов.

### Первоначальная настройка (один раз)

#### 1. Подключить базу данных

1. Открыть `http://<АДРЕС_VPS>:8088`, залогиниться
2. **Настройки** (шестерёнка вверху справа) → **Подключения к базам данных**
3. Кнопка **+ База данных**
4. Тип: **ClickHouse Connect**
5. Строка подключения:
   ```
   clickhousedb://team_XX:team_pass_XX@clickhouse:8123/game_analytics
   ```
6. **Проверить подключение** → зелёная галочка → **Подключить**

Если нужен доступ к своей базе — добавьте второе подключение с `team_XX` вместо `game_analytics`.

### Рабочий цикл: SQL → Dataset → Chart → Dashboard

#### 2. Написать SQL-запрос

1. **SQL** → **SQL Лаборатория**
2. Выбрать базу данных слева
3. Написать запрос, например:
   ```sql
   SELECT
       toDate(event_timestamp) AS date,
       uniqExact(user_id) AS dau
   FROM game_analytics.events
   WHERE event_name = 'session_start'
   GROUP BY date
   ORDER BY date
   ```
4. **Выполнить** (или Ctrl+Enter)
5. Проверить результат в таблице внизу

#### 3. Сохранить как набор данных

1. Над результатами: **Сохранить** → **Сохранить как набор данных**
2. Ввести название: `dau_daily`
3. Сохранить

#### 4. Создать график

1. **Графики** → **+ График**
2. Выбрать набор данных: `dau_daily`
3. Выбрать тип: **Линейный график временных рядов**
4. Настроить:
   - **Ось X**: `date`
   - **Меры**: `MAX(dau)`
   - **Измерения**: пусто (или `platform` если хотите разбивку)
5. **Создать график**
6. **Сохранить** → ввести название → выбрать или создать дашборд

#### 5. Собрать дашборд

1. **Дашборды** → **+ Дашборд**
2. Ввести название
3. Режим редактирования (иконка карандаша)
4. Справа — панель **Графики**. Перетаскивайте графики на холст
5. Двигайте и меняйте размер
6. **Сохранить**

### Типы графиков: что для чего

| Задача | Тип графика |
|--------|------------|
| Метрика по дням (DAU, revenue) | Линейный график временных рядов |
| Сравнение категорий (A/B группы) | Столбчатый график |
| Доли (продукты, платформы) | Круговая диаграмма |
| Retention матрица | Сводная таблица |
| Воронка | Воронковая диаграмма |
| Таблица с числами | Таблица |

### Измерения в графиках

Поле **Измерения** разбивает одну линию на несколько. Если перетащить туда `platform` — будет две линии: iOS и Android. Это аналог дополнительного `GROUP BY` в SQL.

### Фильтры на дашборде

Чтобы добавить интерактивные фильтры (по дате, платформе и т.д.):
1. Открыть дашборд → режим редактирования
2. Иконка фильтра слева → **+ Добавить фильтр**
3. Выбрать колонку для фильтра

---

## 8. Частые проблемы и решения

### Генератор

**Проблема:** `ModuleNotFoundError` при запуске
**Решение:** `pip install -r requirements.txt`

**Проблема:** Генерация занимает слишком долго
**Решение:** Используйте override с уменьшенным объёмом:
```yaml
simulation:
  duration_days: 30
installs:
  total: 10000
```

**Проблема:** Разные запуски с одним seed дают одинаковые данные
**Решение:** Это фича, а не баг. Используйте разные seed для разных экспериментов.

### ClickHouse

**Проблема:** `Code: 516. Authentication failed`
**Решение:** Проверьте логин/пароль. Ваши: `team_XX` / `team_pass_XX`

**Проблема:** `Code: 60. Table doesn't exist`
**Решение:** Для эталонных данных: `game_analytics.events`. Для своих: `team_XX.events`. Проверьте, что данные загружены.

**Проблема:** Запрос медленный
**Решение:** Добавьте фильтр по `event_name` и/или `run_id`. Не используйте `SELECT *`.

### Superset

**Проблема:** «Нет данных для отображения»
**Решение:** Проверьте, что SQL-запрос возвращает данные. Убедитесь, что набор данных подключён к правильной базе.

**Проблема:** Не могу подключить ClickHouse
**Решение:** Убедитесь, что используете `clickhousedb://` (не `clickhouse://`). Порт: `8123`.

### Загрузка данных

**Проблема:** `Error: --run-id is required`
**Решение:** Всегда указывайте `--run-id` при загрузке. Например: `--run-id baseline`

**Проблема:** Хочу перезалить данные
**Решение:** Сначала удалите старый прогон, потом загрузите заново:
```bash
python scripts/load_to_clickhouse.py --delete-run baseline --database team_XX --host <VPS>
python scripts/load_to_clickhouse.py --input ... --run-id baseline --database team_XX --host <VPS>
```
