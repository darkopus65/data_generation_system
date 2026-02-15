-- Создание базы данных
CREATE DATABASE IF NOT EXISTS game_analytics;

-- Основная таблица событий
CREATE TABLE IF NOT EXISTS game_analytics.events
(
    -- Идентификатор прогона генератора
    run_id LowCardinality(String),

    -- Идентификаторы
    event_id String,
    event_name LowCardinality(String),
    event_timestamp DateTime64(3),

    -- Пользователь и сессия
    user_id String,
    session_id String,

    -- Device info
    device_id String,
    platform LowCardinality(String),
    os_version LowCardinality(String),
    app_version LowCardinality(String),
    device_model LowCardinality(String),
    country LowCardinality(String),
    language LowCardinality(String),

    -- User properties
    player_level UInt16,
    vip_level UInt8,
    total_spent_usd Float32,
    days_since_install UInt16,
    cohort_date Date,
    current_chapter UInt8,

    -- A/B тесты (как JSON строка для гибкости)
    ab_tests String,

    -- Event properties (как JSON строка)
    event_properties String,

    -- Служебные поля для партиционирования
    event_date Date DEFAULT toDate(event_timestamp)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (run_id, event_name, user_id, event_timestamp)
SETTINGS index_granularity = 8192;

-- Материализованное представление для быстрых агрегаций по дням
CREATE MATERIALIZED VIEW IF NOT EXISTS game_analytics.events_daily_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (run_id, event_date, event_name, platform, country)
AS SELECT
    run_id,
    toDate(event_timestamp) as event_date,
    event_name,
    platform,
    country,
    count() as event_count,
    uniqExact(user_id) as unique_users,
    uniqExact(session_id) as unique_sessions
FROM game_analytics.events
GROUP BY run_id, event_date, event_name, platform, country;

-- Представление для retention анализа
CREATE MATERIALIZED VIEW IF NOT EXISTS game_analytics.user_retention_mv
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(cohort_date)
ORDER BY (run_id, cohort_date, platform)
AS SELECT
    run_id,
    cohort_date,
    platform,
    uniqState(user_id) as users_d0,
    uniqIfState(user_id, days_since_install >= 1) as users_d1,
    uniqIfState(user_id, days_since_install >= 7) as users_d7,
    uniqIfState(user_id, days_since_install >= 30) as users_d30
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY run_id, cohort_date, platform;

-- Представление для IAP анализа
CREATE MATERIALIZED VIEW IF NOT EXISTS game_analytics.iap_stats_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (run_id, event_date, platform, country)
AS SELECT
    run_id,
    toDate(event_timestamp) as event_date,
    platform,
    country,
    count() as purchases,
    uniqExact(user_id) as paying_users,
    sumIf(
        toFloat64(JSONExtractFloat(event_properties, 'price_usd')),
        event_name = 'iap_purchase'
    ) as revenue_usd
FROM game_analytics.events
WHERE event_name IN ('iap_purchase', 'iap_initiated', 'iap_failed')
GROUP BY run_id, event_date, platform, country;

-- Индекс для быстрого поиска по user_id
ALTER TABLE game_analytics.events ADD INDEX idx_user_id user_id TYPE bloom_filter GRANULARITY 1;

-- Индекс для A/B тестов
ALTER TABLE game_analytics.events ADD INDEX idx_ab_tests ab_tests TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 1;
