# Конфигурация генератора

Полный справочник параметров конфигурации `configs/default.yaml`.

## Содержание

- [Параметры симуляции](#параметры-симуляции)
- [Установки (installs)](#установки-installs)
- [Типы игроков](#типы-игроков)
- [Экономика](#экономика)
- [Gacha](#gacha)
- [Магазин и IAP](#магазин-и-iap)
- [VIP система](#vip-система)
- [Прогрессия](#прогрессия)
- [Герои](#герои)
- [Социальные функции](#социальные-функции)
- [A/B тесты](#ab-тесты)
- [Сценарии](#сценарии)
- [Вывод](#вывод)
- [Устройства](#устройства)

---

## Параметры симуляции

```yaml
simulation:
  seed: 42                        # Random seed для воспроизводимости
  start_date: "2025-01-01"        # Дата начала симуляции (ISO 8601)
  duration_days: 90               # Длительность в днях (1-365)
```

| Параметр | Тип | Диапазон | Описание |
|----------|-----|----------|----------|
| `seed` | int | любое | Seed для генератора случайных чисел. Одинаковый seed = одинаковые данные |
| `start_date` | string | ISO 8601 | Дата первого дня симуляции |
| `duration_days` | int | 1-365 | Сколько дней симулировать |

---

## Установки (installs)

```yaml
installs:
  total: 50000                    # Всего установок за период
  distribution: "decay"           # Распределение по дням
  decay_rate: 0.02                # Скорость затухания (для decay)

  sources:                        # Источники трафика
    organic:
      share: 0.40                 # Доля от всех установок
      retention_modifier: 1.0     # Модификатор retention
      monetization_modifier: 1.0  # Модификатор монетизации
    google_ads:
      share: 0.25
      retention_modifier: 0.9
      monetization_modifier: 1.1
    # ...
```

### Параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `total` | int | Общее количество установок за весь период |
| `distribution` | string | `decay` (экспоненциальное затухание) или `uniform` (равномерное) |
| `decay_rate` | float | Скорость затухания для `decay` распределения |

### Источники трафика

Сумма `share` всех источников должна равняться 1.0.

| Параметр | Тип | Описание |
|----------|-----|----------|
| `share` | float | Доля от общего числа установок (0-1) |
| `retention_modifier` | float | Множитель retention (1.0 = базовый) |
| `monetization_modifier` | float | Множитель вероятности покупок |

**Предзаданные источники:**

| Источник | Доля | Retention | Monetization | Описание |
|----------|------|-----------|--------------|----------|
| `organic` | 40% | ×1.0 | ×1.0 | Органический трафик |
| `google_ads` | 25% | ×0.9 | ×1.1 | Google Ads |
| `facebook` | 20% | ×0.85 | ×1.05 | Meta Ads |
| `unity_ads` | 10% | ×0.75 | ×0.8 | Unity Ads |
| `influencer` | 5% | ×1.1 | ×0.9 | Influencer marketing |

---

## Типы игроков

```yaml
player_types:
  whale:
    share: 0.003                  # 0.3% игроков
    spending_monthly_usd: [100, 500]  # Траты в месяц (min, max)
    sessions_per_day: [3, 6]      # Сессий в день (min, max)
    session_duration_min: [15, 45]  # Длительность сессии в минутах
    retention:
      d1: 0.85                    # Retention day 1
      d7: 0.70                    # Retention day 7
      d30: 0.55                   # Retention day 30
      d90: 0.40                   # Retention day 90
    ad_watch_probability: 0.1     # Вероятность смотреть рекламу
    gacha_desire: 0.7             # Базовое желание крутить гачу
    arena_engagement: 0.95        # Вовлечённость в арену
    guild_engagement: 0.90        # Вовлечённость в гильдию
```

### Параметры типа игрока

| Параметр | Тип | Описание |
|----------|-----|----------|
| `share` | float | Доля от всех игроков (сумма всех = 1.0) |
| `spending_monthly_usd` | [min, max] | Диапазон трат в месяц (USD) |
| `sessions_per_day` | [min, max] | Количество сессий в день |
| `session_duration_min` | [min, max] | Длительность сессии (минуты) |
| `retention.d1` | float | Retention на день 1 (0-1) |
| `retention.d7` | float | Retention на день 7 (должен быть ≤ d1) |
| `retention.d30` | float | Retention на день 30 (должен быть ≤ d7) |
| `retention.d90` | float | Retention на день 90 (должен быть ≤ d30) |
| `ad_watch_probability` | float | Вероятность просмотра рекламы (0-1) |
| `gacha_desire` | float | Базовая склонность к гаче (0-1) |
| `arena_engagement` | float | Вероятность играть в арену (0-1) |
| `guild_engagement` | float | Вероятность участвовать в гильдии (0-1) |

### Предзаданные типы

| Тип | Доля | Траты/мес | D1 | D7 | D30 | Описание |
|-----|------|-----------|----|----|-----|----------|
| `whale` | 0.3% | $100-500 | 85% | 70% | 55% | Киты |
| `dolphin` | 1.2% | $10-100 | 70% | 45% | 25% | Дельфины |
| `minnow` | 3.5% | $1-15 | 55% | 30% | 12% | Мелкие плательщики |
| `free_engaged` | 25% | $0 | 50% | 25% | 10% | Активные F2P |
| `free_casual` | 45% | $0 | 40% | 15% | 5% | Казуальные F2P |
| `free_churner` | 25% | $0 | 25% | 5% | 1% | Быстро уходят |

---

## Экономика

```yaml
economy:
  initial:
    gold: 1000                    # Стартовое золото
    gems: 100                     # Стартовые гемы
    summon_tickets: 5             # Стартовые тикеты призыва
    energy: 120                   # Стартовая энергия

  energy:
    max: 120                      # Максимум энергии
    regen_minutes: 5              # Минут на 1 единицу энергии
    stage_cost: 6                 # Стоимость входа в уровень

  stage_rewards:
    gold_base: 100                # Базовая награда золотом
    gold_per_chapter: 50          # +золото за главу
    exp_base: 20                  # Базовый опыт
    exp_per_chapter: 10           # +опыт за главу

  idle_rewards:
    gold_per_hour_base: 500       # Базовый idle доход в час
    gold_per_stage_mult: 0.05     # Множитель за пройденные уровни
    max_hours: 12                 # Максимум накопления

  hero_levelup:
    gold_base: 100                # Базовая цена прокачки
    gold_per_level_mult: 1.15     # Множитель роста цены
```

---

## Gacha

```yaml
gacha:
  single_gems: 300                # Цена одиночного призыва
  multi_gems: 2700                # Цена 10 призывов (скидка 10%)

  rates:
    common: 0.60                  # 60% шанс common
    rare: 0.30                    # 30% шанс rare
    epic: 0.08                    # 8% шанс epic
    legendary: 0.02               # 2% шанс legendary

  pity:
    threshold: 90                 # Гарантия legendary на 90-м призыве
    soft_pity_start: 75           # Начало soft pity
    soft_pity_rate_boost: 0.05    # +5% шанс legendary за каждый призыв после soft pity
```

### Pity система

1. **Soft Pity** (с 75 призыва): шанс legendary увеличивается на 5% за каждый призыв
2. **Hard Pity** (90 призыв): гарантированный legendary
3. Счётчик сбрасывается при получении legendary

---

## Магазин и IAP

```yaml
shop:
  products:
    starter_pack:
      price_usd: 0.99
      gems: 500
      summon_tickets: 10
      limit: 1                    # Разовая покупка
    gems_tier1:
      price_usd: 4.99
      gems: 500
    gems_tier2:
      price_usd: 9.99
      gems: 1100
    gems_tier3:
      price_usd: 19.99
      gems: 2400
    gems_tier4:
      price_usd: 49.99
      gems: 6500
    gems_tier5:
      price_usd: 99.99
      gems: 14000
    monthly_pass:
      price_usd: 4.99
      gems_immediate: 300
      gems_daily: 100
      duration_days: 30

  ads:
    reward_gems: 50               # Награда за просмотр рекламы
    max_per_day: 5                # Лимит просмотров в день
    cooldown_minutes: 30          # Кулдаун между просмотрами
```

---

## VIP система

```yaml
vip:
  levels:
    0: { threshold: 0, energy_bonus: 0, gold_bonus: 0 }
    1: { threshold: 5, energy_bonus: 10, gold_bonus: 0 }
    2: { threshold: 15, energy_bonus: 10, gold_bonus: 0 }
    3: { threshold: 30, energy_bonus: 10, gold_bonus: 0.2 }
    # ... до уровня 10
    10: { threshold: 5000, energy_bonus: 40, gold_bonus: 1.0 }
```

| Параметр | Описание |
|----------|----------|
| `threshold` | Минимум потраченных USD для достижения уровня |
| `energy_bonus` | Бонус к максимуму энергии |
| `gold_bonus` | Процент бонуса к добыче золота (0.2 = 20%) |

---

## Прогрессия

```yaml
progression:
  chapters: 20                    # Количество глав
  stages_per_chapter: 10          # Уровней в главе (всего 200)

  stage_power:
    base: 100                     # Требование силы для уровня 1
    per_stage_mult: 1.08          # Рост требования за уровень

  player_level:
    max: 100                      # Максимальный уровень игрока
    exp_per_level_base: 100       # Базовый опыт для levelup
    exp_per_level_mult: 1.12      # Рост требования опыта

  unlocks:
    gacha: 3                      # Гача открывается на уровне 3
    daily_quests: 5               # Квесты на уровне 5
    events: 5                     # События на уровне 5
    arena: 10                     # Арена на уровне 10
    guild: 15                     # Гильдии на уровне 15
```

---

## Герои

```yaml
heroes:
  pool:
    common: 20                    # 20 common героев
    rare: 15                      # 15 rare героев
    epic: 10                      # 10 epic героев
    legendary: 5                  # 5 legendary героев

  base_power:
    common: 50
    rare: 100
    epic: 200
    legendary: 400

  power_per_level: 10             # +сила за уровень
  power_per_star_mult: 1.2        # ×1.2 за каждую звезду
```

---

## Социальные функции

```yaml
social:
  arena:
    daily_attempts: 5             # Бесплатных попыток в день
    attempt_cost_gems: 50         # Цена доп. попытки
    rating_start: 1000            # Стартовый рейтинг
    rating_k_factor: 32           # K-factor для ELO

  guilds:
    count: 500                    # Количество гильдий
    max_members: 30               # Максимум участников
    boss_daily_attempts: 1        # Атак босса в день
```

---

## A/B тесты

```yaml
ab_tests:
  test_name:
    enabled: true                 # Включен ли тест
    variants: ["control", "variant_a", "variant_b"]
    weights: [0.33, 0.33, 0.34]   # Распределение (сумма = 1.0)
    activation_condition: null    # Условие активации (опционально)
    effects:
      variant_a:
        some_parameter: value
```

Подробнее см. [A/B тесты](AB_TESTS.md).

---

## Сценарии

```yaml
scenarios:
  bad_traffic:
    enabled: true                 # Включить сценарий
    day: 25                       # День симуляции
    source_name: "fake_network"   # Название источника
    volume: 2000                  # Количество установок
    retention_modifier: 0.3       # Модификатор retention
    monetization_modifier: 0.1    # Модификатор монетизации
    bot_ratio: 0.4                # Доля ботов (0-1)
```

---

## Вывод

```yaml
output:
  format: "jsonl"                 # jsonl | parquet | both
  compression: "gzip"             # none | gzip (для jsonl)
  batch_size: 10000               # Событий на batch запись
  include_metadata: true          # Генерировать metadata.json
```

---

## Устройства

```yaml
devices:
  platforms:
    ios: 0.45                     # 45% iOS
    android: 0.55                 # 55% Android

  countries:
    RU: 0.40
    US: 0.15
    DE: 0.10
    BR: 0.10
    JP: 0.08
    KR: 0.07
    other: 0.10

  ios_models:
    - "iPhone 12"
    - "iPhone 13"
    - "iPhone 14"
    - "iPhone 15"
    - "iPad Air"

  android_models:
    - "Samsung Galaxy S21"
    - "Samsung Galaxy S22"
    - "Pixel 6"
    - "Pixel 7"
    - "Xiaomi 12"

  app_versions: ["1.0.0", "1.0.1", "1.1.0", "1.2.0"]
  app_version_weights: [0.05, 0.10, 0.25, 0.60]
```

---

## Override файлы

Можно переопределить любые параметры в override файле:

```yaml
# configs/overrides/my_scenario.yaml
simulation:
  duration_days: 30

installs:
  total: 10000

player_types:
  whale:
    share: 0.01  # Увеличить долю китов до 1%
```

Запуск:
```bash
python generate.py --override configs/overrides/my_scenario.yaml
```

Несколько override (применяются последовательно):
```bash
python generate.py -o override1.yaml -o override2.yaml
```
