# Инфраструктура для Game Analytics Course

Развёртывание ClickHouse + Apache Superset для учебного курса.

## Быстрый старт

### 1. Запуск инфраструктуры

```bash
cd infrastructure
docker-compose up -d
```

Первый запуск займёт несколько минут для инициализации.

### 2. Проверка статуса

```bash
docker-compose ps
```

Все контейнеры должны быть в статусе `running`.

### 3. Генерация данных

```bash
cd ..
python generate.py --seed 42
```

### 4. Загрузка данных в ClickHouse

```bash
# Установить драйвер ClickHouse
pip install clickhouse-connect

# Загрузить данные
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --run-id baseline
```

### 5. Доступ к системам

| Система | URL | Логин | Пароль |
|---------|-----|-------|--------|
| **Superset** | http://localhost:8088 | admin | admin123 |
| **ClickHouse HTTP** | http://localhost:8123 | admin | admin123 |
| **ClickHouse Native** | localhost:9000 | admin | admin123 |

---

## Настройка Superset

### Добавление ClickHouse как источника данных

1. Войдите в Superset: http://localhost:8088
2. Перейдите в **Settings** → **Database Connections**
3. Нажмите **+ Database**
4. Выберите **ClickHouse Connect**
5. Введите connection string:

```
clickhousedb://superset:superset123@clickhouse:9000/game_analytics
```

Или используйте форму:
- **Host**: clickhouse
- **Port**: 8123
- **Database**: game_analytics
- **Username**: superset
- **Password**: superset123

### Создание датасетов

После подключения базы:

1. **Settings** → **Datasets** → **+ Dataset**
2. Выберите базу `game_analytics`
3. Выберите таблицу `events`
4. Сохраните

Теперь можно создавать чарты и дашборды!

---

## Пользователи

### ClickHouse

| Пользователь | Пароль | Права |
|--------------|--------|-------|
| admin | admin123 | Полные права |
| student | student123 | Только чтение game_analytics |
| superset | superset123 | Чтение game_analytics |

### Superset

| Пользователь | Пароль | Роль |
|--------------|--------|------|
| admin | admin123 | Admin |
| team_XX | superset_team_XX | Gamma + team_XX_role |

Командные аккаунты создаются автоматически через `python scripts/setup_superset_teams.py`.

---

## Полезные SQL запросы

### Проверка данных

```sql
-- Количество событий
SELECT count() FROM game_analytics.events;

-- События по типам
SELECT event_name, count() as cnt
FROM game_analytics.events
GROUP BY event_name
ORDER BY cnt DESC;

-- Уникальные пользователи
SELECT uniqExact(user_id) as users
FROM game_analytics.events;
```

### Retention анализ

```sql
-- D1/D7/D30 Retention по когортам
SELECT
    cohort_date,
    uniqExact(user_id) as d0_users,
    uniqExactIf(user_id, days_since_install >= 1) as d1_users,
    uniqExactIf(user_id, days_since_install >= 7) as d7_users,
    uniqExactIf(user_id, days_since_install >= 30) as d30_users,
    round(d1_users / d0_users * 100, 2) as d1_retention,
    round(d7_users / d0_users * 100, 2) as d7_retention,
    round(d30_users / d0_users * 100, 2) as d30_retention
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY cohort_date
ORDER BY cohort_date;
```

### A/B тест анализ

```sql
-- Сравнение групп A/B теста onboarding_length
SELECT
    JSONExtractString(ab_tests, 'onboarding_length') as ab_group,
    uniqExact(user_id) as users,
    countIf(event_name = 'iap_purchase') as purchases,
    sumIf(
        JSONExtractFloat(event_properties, 'price_usd'),
        event_name = 'iap_purchase'
    ) as revenue
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'onboarding_length') != ''
GROUP BY ab_group;
```

### Воронка конверсии

```sql
-- Воронка: install → tutorial → gacha → purchase
WITH funnel AS (
    SELECT
        user_id,
        maxIf(1, event_name = 'session_start' AND JSONExtractBool(event_properties, 'is_first_session')) as step1_install,
        maxIf(1, event_name = 'tutorial_complete') as step2_tutorial,
        maxIf(1, event_name = 'gacha_summon') as step3_gacha,
        maxIf(1, event_name = 'iap_purchase') as step4_purchase
    FROM game_analytics.events
    GROUP BY user_id
)
SELECT
    sum(step1_install) as installs,
    sum(step2_tutorial) as tutorial_complete,
    sum(step3_gacha) as did_gacha,
    sum(step4_purchase) as did_purchase,
    round(tutorial_complete / installs * 100, 2) as tutorial_rate,
    round(did_gacha / installs * 100, 2) as gacha_rate,
    round(did_purchase / installs * 100, 2) as conversion_rate
FROM funnel;
```

---

## Работа с прогонами (run_id)

Каждая загрузка данных маркируется идентификатором прогона (`run_id`). Это позволяет загружать несколько датасетов в одну таблицу и сравнивать метрики между ними.

### Загрузка нескольких прогонов

```bash
# Базовый датасет
python generate.py --seed 42
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --run-id baseline

# Эксперимент с быстрой энергией
python generate.py --seed 42 --override configs/overrides/small_test.yaml
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --run-id exp_small_test

# Эксперимент с плохим трафиком
python generate.py --seed 42 --override configs/overrides/bad_traffic.yaml
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --run-id exp_bad_traffic
```

### Просмотр загруженных прогонов

```sql
SELECT run_id, count() as events, uniqExact(user_id) as users
FROM game_analytics.events
GROUP BY run_id
ORDER BY run_id;
```

### Сравнение метрик между прогонами

```sql
-- Ключевые метрики по прогонам
SELECT
    run_id,
    uniqExact(user_id) as total_users,
    countIf(event_name = 'iap_purchase') as total_purchases,
    uniqExactIf(user_id, event_name = 'iap_purchase') as paying_users,
    round(paying_users / total_users * 100, 2) as conversion_pct,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') as revenue
FROM game_analytics.events
GROUP BY run_id
ORDER BY run_id;
```

### Удаление прогона

```bash
# Удалить данные конкретного прогона
python scripts/load_to_clickhouse.py --delete-run exp_bad_traffic

# Перезагрузить прогон (удалить старые данные + загрузить новые)
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --run-id baseline --truncate
```

---

## Командная работа

Для курса предусмотрена изолированная инфраструктура для каждой команды.

### Настройка команд

```bash
# Создать базы и пользователей для 13 команд
python scripts/setup_teams.py --teams 13

# Удалить все командные базы и пользователей
python scripts/setup_teams.py --teams 13 --drop
```

Скрипт создаст файл `teams_credentials.csv` с логинами и паролями.

### Структура доступов

| Что | Команда | Права |
|-----|---------|-------|
| `game_analytics.*` | Все команды | Только чтение (SELECT) |
| `team_XX.*` | team_XX | Полный доступ (ALL) |

Каждая команда:
- **Читает** эталонные данные из `game_analytics.events`
- **Пишет** свои данные в `team_XX.events`
- **Создаёт** свои таблицы в `team_XX`

### Подключение команд к ClickHouse

```bash
# Подключение через CLI
clickhouse-client --host localhost --port 9000 \
    --user team_01 --password team_pass_01

# Подключение из Python
import clickhouse_connect
client = clickhouse_connect.get_client(
    host='localhost', port=8123,
    username='team_01', password='team_pass_01',
    database='team_01'
)
```

### Загрузка данных в командную базу

```bash
# Генерация данных с нужными параметрами
python generate.py --seed 100

# Загрузка в базу команды
python scripts/load_to_clickhouse.py \
    --input output/run_*/events.jsonl.gz \
    --run-id my_experiment \
    --database team_01 \
    --user team_01 \
    --password team_pass_01
```

### Настройка Superset для команд (автоматическая)

Скрипт `setup_superset_teams.py` автоматически создаёт для каждой команды:
- Подключение к базе данных в Superset (видно в SQL Lab)
- Роль с доступом к SQL Lab + только к своей БД и shared game_analytics
- Пользователя Superset с изолированным доступом

```bash
# Создать пользователей, роли и подключения для 15 команд
python scripts/setup_superset_teams.py --teams 15

# Удалить все командные конфигурации из Superset
python scripts/setup_superset_teams.py --teams 15 --drop
```

Скрипт создаст файл `superset_teams_credentials.csv` с логинами.

**Порядок запуска** (если настраиваете с нуля):
```bash
# 1. Запустить инфраструктуру
cd infrastructure && docker-compose up -d && cd ..

# 2. Создать ClickHouse базы и пользователей для команд
python scripts/setup_teams.py --teams 15

# 3. Создать shared подключение и дашборды в Superset
python scripts/setup_superset_dashboards.py

# 4. Создать изолированные аккаунты команд в Superset
python scripts/setup_superset_teams.py --teams 15
```

**Что видит каждая команда после входа в Superset:**
- Вкладку **SQL Lab** для написания SQL запросов
- В dropdown баз данных: только **"Team XX"** (своя) и **"ClickHouse Game Analytics"** (shared)
- Только свои датасеты и сохранённые запросы

**Параметры скрипта:**
```bash
python scripts/setup_superset_teams.py \
    --teams 15 \                              # количество команд
    --clickhouse-password-prefix team_pass_ \ # префикс CH паролей
    --superset-password-prefix superset_team_ \ # префикс Superset паролей
    --output superset_teams_credentials.csv
```

Для ручного подключения (без скрипта) используйте connection string:
```
clickhousedb://team_01:team_pass_01@clickhouse:8123/team_01
```

---

## Troubleshooting

### ClickHouse не запускается

```bash
# Проверить логи
docker-compose logs clickhouse

# Проверить, свободен ли порт
lsof -i :8123
lsof -i :9000
```

### Superset не видит ClickHouse

1. Убедитесь, что контейнеры в одной сети:
```bash
docker network inspect infrastructure_default
```

2. Проверьте доступность изнутри контейнера:
```bash
docker exec -it superset curl http://clickhouse:8123
```

### Ошибка загрузки данных

```bash
# Проверить, что таблица существует
docker exec -it clickhouse clickhouse-client \
    --user admin --password admin123 \
    --query "SHOW TABLES FROM game_analytics"
```

---

## Остановка и очистка

```bash
# Остановить контейнеры
docker-compose down

# Остановить и удалить данные
docker-compose down -v
```

---

## Масштабирование

Для большого количества студентов рекомендуется:

1. **Выделить больше ресурсов ClickHouse** в docker-compose.yml
2. **Добавить реплики** для чтения
3. **Использовать managed ClickHouse** (Yandex Cloud, ClickHouse Cloud)
