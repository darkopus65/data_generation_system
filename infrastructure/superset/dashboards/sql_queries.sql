-- ============================================================================
-- SQL запросы для дашбордов Superset
-- Создать как Saved Queries или использовать в Virtual Datasets
-- ============================================================================

-- ============================================================================
-- RETENTION DASHBOARD
-- ============================================================================

-- 1. Daily Active Users (DAU)
-- Тип чарта: Line Chart (time-series)
SELECT
    toDate(event_timestamp) as date,
    uniqExact(user_id) as dau
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY date
ORDER BY date;

-- 2. Retention по когортам (D1, D7, D30)
-- Тип чарта: Heatmap или Table
SELECT
    cohort_date,
    uniqExact(user_id) as d0_users,
    uniqExactIf(user_id, days_since_install >= 1) as d1_users,
    uniqExactIf(user_id, days_since_install >= 7) as d7_users,
    uniqExactIf(user_id, days_since_install >= 14) as d14_users,
    uniqExactIf(user_id, days_since_install >= 30) as d30_users,
    round(uniqExactIf(user_id, days_since_install >= 1) / uniqExact(user_id) * 100, 2) as d1_retention,
    round(uniqExactIf(user_id, days_since_install >= 7) / uniqExact(user_id) * 100, 2) as d7_retention,
    round(uniqExactIf(user_id, days_since_install >= 14) / uniqExact(user_id) * 100, 2) as d14_retention,
    round(uniqExactIf(user_id, days_since_install >= 30) / uniqExact(user_id) * 100, 2) as d30_retention
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY cohort_date
HAVING d0_users > 100
ORDER BY cohort_date;

-- 3. Установки по дням и источникам
-- Тип чарта: Stacked Area Chart
SELECT
    toDate(event_timestamp) as date,
    JSONExtractString(event_properties, 'install_source') as install_source,
    uniqExactIf(user_id, JSONExtractBool(event_properties, 'is_first_session')) as installs
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY date, install_source
ORDER BY date, install_source;

-- 4. Среднее количество сессий на пользователя
-- Тип чарта: Line Chart
SELECT
    toDate(event_timestamp) as date,
    count() as sessions,
    uniqExact(user_id) as users,
    round(sessions / users, 2) as sessions_per_user
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY date
ORDER BY date;

-- 5. Средняя длительность сессии
-- Тип чарта: Line Chart
SELECT
    toDate(event_timestamp) as date,
    round(avg(JSONExtractInt(event_properties, 'session_duration_sec')) / 60, 2) as avg_session_min
FROM game_analytics.events
WHERE event_name = 'session_end'
GROUP BY date
ORDER BY date;

-- 6. Retention матрица (для Pivot Table)
-- Тип чарта: Pivot Table
SELECT
    cohort_date,
    days_since_install as day_n,
    uniqExact(user_id) as users
FROM game_analytics.events
WHERE event_name = 'session_start'
    AND days_since_install <= 30
GROUP BY cohort_date, days_since_install
ORDER BY cohort_date, days_since_install;


-- ============================================================================
-- MONETIZATION DASHBOARD
-- ============================================================================

-- 7. Revenue по дням
-- Тип чарта: Line Chart
SELECT
    toDate(event_timestamp) as date,
    sum(JSONExtractFloat(event_properties, 'price_usd')) as revenue_usd,
    uniqExact(user_id) as paying_users,
    count() as transactions
FROM game_analytics.events
WHERE event_name = 'iap_purchase'
GROUP BY date
ORDER BY date;

-- 8. ARPDAU (Average Revenue Per Daily Active User)
-- Тип чарта: Line Chart
WITH
    dau AS (
        SELECT
            toDate(event_timestamp) as date,
            uniqExact(user_id) as users
        FROM game_analytics.events
        WHERE event_name = 'session_start'
        GROUP BY date
    ),
    revenue AS (
        SELECT
            toDate(event_timestamp) as date,
            sum(JSONExtractFloat(event_properties, 'price_usd')) as revenue_usd
        FROM game_analytics.events
        WHERE event_name = 'iap_purchase'
        GROUP BY date
    )
SELECT
    dau.date,
    dau.users as dau,
    coalesce(revenue.revenue_usd, 0) as revenue,
    round(coalesce(revenue.revenue_usd, 0) / dau.users, 4) as arpdau
FROM dau
LEFT JOIN revenue ON dau.date = revenue.date
ORDER BY dau.date;

-- 9. Конверсия в платящих по когортам
-- Тип чарта: Bar Chart
SELECT
    cohort_date,
    uniqExact(user_id) as total_users,
    uniqExactIf(user_id, event_name = 'iap_purchase') as paying_users,
    round(paying_users / total_users * 100, 2) as conversion_pct
FROM game_analytics.events
GROUP BY cohort_date
ORDER BY cohort_date;

-- 10. Распределение покупок по продуктам
-- Тип чарта: Pie Chart или Bar Chart
SELECT
    JSONExtractString(event_properties, 'product_id') as product_id,
    JSONExtractString(event_properties, 'product_name') as product_name,
    count() as purchases,
    sum(JSONExtractFloat(event_properties, 'price_usd')) as revenue_usd,
    uniqExact(user_id) as unique_buyers
FROM game_analytics.events
WHERE event_name = 'iap_purchase'
GROUP BY product_id, product_name
ORDER BY revenue_usd DESC;

-- 11. VIP Level Distribution
-- Тип чарта: Pie Chart
SELECT
    vip_level,
    uniqExact(user_id) as users
FROM game_analytics.events
WHERE event_name = 'player_state_snapshot'
    AND toDate(event_timestamp) = (SELECT max(toDate(event_timestamp)) FROM game_analytics.events)
GROUP BY vip_level
ORDER BY vip_level;

-- 12. LTV по когортам (накопленный Revenue)
-- Тип чарта: Line Chart
SELECT
    cohort_date,
    days_since_install,
    sum(sum(JSONExtractFloat(event_properties, 'price_usd')))
        OVER (PARTITION BY cohort_date ORDER BY days_since_install) as cumulative_revenue,
    uniqExact(user_id) OVER (PARTITION BY cohort_date) as cohort_size,
    round(cumulative_revenue / cohort_size, 2) as ltv
FROM game_analytics.events
WHERE event_name = 'iap_purchase'
GROUP BY cohort_date, days_since_install
ORDER BY cohort_date, days_since_install;


-- ============================================================================
-- A/B TESTS DASHBOARD
-- ============================================================================

-- 13. A/B Test: onboarding_length - Retention
-- Тип чарта: Grouped Bar Chart
SELECT
    JSONExtractString(ab_tests, 'onboarding_length') as ab_group,
    uniqExact(user_id) as users,
    uniqExactIf(user_id, days_since_install >= 1) as d1_users,
    uniqExactIf(user_id, days_since_install >= 7) as d7_users,
    round(d1_users / users * 100, 2) as d1_retention,
    round(d7_users / users * 100, 2) as d7_retention
FROM game_analytics.events
WHERE event_name = 'session_start'
    AND JSONExtractString(ab_tests, 'onboarding_length') != ''
GROUP BY ab_group
ORDER BY ab_group;

-- 14. A/B Test: onboarding_length - Conversion
-- Тип чарта: Grouped Bar Chart
SELECT
    JSONExtractString(ab_tests, 'onboarding_length') as ab_group,
    uniqExact(user_id) as total_users,
    uniqExactIf(user_id, event_name = 'iap_purchase') as paying_users,
    round(paying_users / total_users * 100, 2) as conversion_pct,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') as revenue,
    round(revenue / total_users, 2) as arpu
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'onboarding_length') != ''
GROUP BY ab_group
ORDER BY ab_group;

-- 15. A/B Test: starter_pack_price
-- Тип чарта: Table
SELECT
    JSONExtractString(ab_tests, 'starter_pack_price') as ab_group,
    uniqExact(user_id) as users,
    uniqExactIf(user_id, event_name = 'iap_purchase') as payers,
    round(payers / users * 100, 2) as conversion_pct,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') as revenue,
    round(revenue / users, 2) as arpu,
    round(revenue / payers, 2) as arppu
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'starter_pack_price') != ''
GROUP BY ab_group
ORDER BY ab_group;

-- 16. A/B Test: gacha_pity_display - Gacha Activity
-- Тип чарта: Table
SELECT
    JSONExtractString(ab_tests, 'gacha_pity_display') as ab_group,
    uniqExact(user_id) as users,
    countIf(event_name = 'gacha_summon') as total_pulls,
    round(total_pulls / users, 2) as pulls_per_user,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') as revenue
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'gacha_pity_display') != ''
GROUP BY ab_group
ORDER BY ab_group;

-- 17. Все A/B тесты - сводка
-- Тип чарта: Table
SELECT
    'onboarding_length' as test_name,
    JSONExtractString(ab_tests, 'onboarding_length') as variant,
    uniqExact(user_id) as users,
    round(uniqExactIf(user_id, days_since_install >= 7) / uniqExact(user_id) * 100, 2) as d7_retention,
    round(uniqExactIf(user_id, event_name = 'iap_purchase') / uniqExact(user_id) * 100, 2) as conversion
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'onboarding_length') != ''
GROUP BY variant

UNION ALL

SELECT
    'starter_pack_price' as test_name,
    JSONExtractString(ab_tests, 'starter_pack_price') as variant,
    uniqExact(user_id) as users,
    round(uniqExactIf(user_id, days_since_install >= 7) / uniqExact(user_id) * 100, 2) as d7_retention,
    round(uniqExactIf(user_id, event_name = 'iap_purchase') / uniqExact(user_id) * 100, 2) as conversion
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'starter_pack_price') != ''
GROUP BY variant

UNION ALL

SELECT
    'gacha_pity_display' as test_name,
    JSONExtractString(ab_tests, 'gacha_pity_display') as variant,
    uniqExact(user_id) as users,
    round(uniqExactIf(user_id, days_since_install >= 7) / uniqExact(user_id) * 100, 2) as d7_retention,
    round(uniqExactIf(user_id, event_name = 'iap_purchase') / uniqExact(user_id) * 100, 2) as conversion
FROM game_analytics.events
WHERE JSONExtractString(ab_tests, 'gacha_pity_display') != ''
GROUP BY variant

ORDER BY test_name, variant;


-- ============================================================================
-- FUNNEL & ENGAGEMENT DASHBOARD
-- ============================================================================

-- 18. Воронка конверсии
-- Тип чарта: Funnel Chart
WITH user_funnel AS (
    SELECT
        user_id,
        max(event_name = 'session_start' AND JSONExtractBool(event_properties, 'is_first_session')) as step1_install,
        max(event_name = 'tutorial_complete') as step2_tutorial,
        max(event_name = 'gacha_summon') as step3_gacha,
        max(event_name = 'iap_purchase') as step4_purchase
    FROM game_analytics.events
    GROUP BY user_id
)
SELECT
    'Install' as step,
    1 as step_order,
    sum(step1_install) as users
FROM user_funnel

UNION ALL

SELECT
    'Tutorial Complete' as step,
    2 as step_order,
    sum(step2_tutorial) as users
FROM user_funnel

UNION ALL

SELECT
    'First Gacha' as step,
    3 as step_order,
    sum(step3_gacha) as users
FROM user_funnel

UNION ALL

SELECT
    'First Purchase' as step,
    4 as step_order,
    sum(step4_purchase) as users
FROM user_funnel

ORDER BY step_order;

-- 19. События по типам
-- Тип чарта: Pie Chart или Bar Chart
SELECT
    event_name,
    count() as event_count
FROM game_analytics.events
GROUP BY event_name
ORDER BY event_count DESC
LIMIT 20;

-- 20. Progression: Главы прохождения
-- Тип чарта: Bar Chart
SELECT
    JSONExtractInt(event_properties, 'chapter') as chapter,
    uniqExact(user_id) as users_reached,
    count() as completions
FROM game_analytics.events
WHERE event_name = 'stage_complete'
GROUP BY chapter
ORDER BY chapter;

-- 21. Источники трафика - качество
-- Тип чарта: Table
SELECT
    JSONExtractString(event_properties, 'install_source') as source,
    uniqExact(user_id) as installs,
    round(uniqExactIf(user_id, days_since_install >= 1) / uniqExact(user_id) * 100, 2) as d1_retention,
    round(uniqExactIf(user_id, days_since_install >= 7) / uniqExact(user_id) * 100, 2) as d7_retention,
    round(uniqExactIf(user_id, event_name = 'iap_purchase') / uniqExact(user_id) * 100, 2) as conversion_pct,
    round(sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') / uniqExact(user_id), 2) as arpu
FROM game_analytics.events
WHERE event_name IN ('session_start', 'iap_purchase')
GROUP BY source
ORDER BY installs DESC;

-- 22. Платформы
-- Тип чарта: Pie Chart
SELECT
    platform,
    uniqExact(user_id) as users,
    count() as events
FROM game_analytics.events
GROUP BY platform;

-- 23. Страны
-- Тип чарта: World Map или Bar Chart
SELECT
    country,
    uniqExact(user_id) as users,
    sumIf(JSONExtractFloat(event_properties, 'price_usd'), event_name = 'iap_purchase') as revenue
FROM game_analytics.events
GROUP BY country
ORDER BY users DESC
LIMIT 20;


-- ============================================================================
-- ANOMALY DETECTION (Bad Traffic)
-- ============================================================================

-- 24. Качество трафика по дням и источникам
-- Тип чарта: Line Chart с facet по source
SELECT
    toDate(event_timestamp) as date,
    JSONExtractString(event_properties, 'install_source') as source,
    uniqExactIf(user_id, JSONExtractBool(event_properties, 'is_first_session')) as installs,
    round(uniqExactIf(user_id, days_since_install >= 1) /
          uniqExactIf(user_id, JSONExtractBool(event_properties, 'is_first_session')) * 100, 2) as d1_retention
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY date, source
HAVING installs > 10
ORDER BY date, source;

-- 25. Anomaly: Резкое падение retention
-- Тип чарта: Line Chart с annotation
SELECT
    cohort_date,
    uniqExact(user_id) as cohort_size,
    round(uniqExactIf(user_id, days_since_install >= 1) / uniqExact(user_id) * 100, 2) as d1_retention,
    -- Флаг аномалии: retention ниже 15% при размере когорты > 500
    CASE
        WHEN uniqExact(user_id) > 500
             AND uniqExactIf(user_id, days_since_install >= 1) / uniqExact(user_id) < 0.15
        THEN 'ANOMALY'
        ELSE 'OK'
    END as status
FROM game_analytics.events
WHERE event_name = 'session_start'
GROUP BY cohort_date
ORDER BY cohort_date;
