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
    --truncate
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

Для добавления студентов используйте **Settings** → **List Users** → **+ User**.

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
