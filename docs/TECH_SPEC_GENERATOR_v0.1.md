# Technical Specification: Data Generator v0.1
## "Idle Champions: Synthetic"

**Статус:** Утверждён  
**Дата:** 2025-02-01  
**Связан с:** GDD v0.2, Event Taxonomy v0.2, AB_TESTS_CONFIG v0.1, AGENT_BEHAVIOR_MODEL v0.1

---

## 1. Обзор

### 1.1. Назначение

Генератор синтетических данных игровой аналитики для учебных целей.

**Входные данные:** Конфигурационные файлы (YAML)
**Выходные данные:** Event-логи в формате JSONL/Parquet для загрузки в ClickHouse

### 1.2. Ключевые требования

| Требование | Описание |
|------------|----------|
| Детерминированность | Одинаковый seed → одинаковые данные |
| Масштабируемость | 50K–100K игроков, 90 дней, 10–50M событий |
| Валидация | Проверка корректности конфигов перед запуском |
| Модульность | Легко менять параметры через конфиги |
| Воспроизводимость | Возможность пересоздать точно такой же датасет |

### 1.3. Ограничения

- Генерация только офлайн (batch), не real-time
- Один запуск = один датасет
- Нет UI, только CLI

---

## 2. Архитектура

### 2.1. Высокоуровневая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                    (python generate.py ...)                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Config Loader & Validator                   │
│                 (загрузка YAML, валидация, merge)                │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Simulation Engine                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Agent Factory │  │  World State │  │  Event Emitter       │   │
│  │ (создание    │  │  (баннеры,   │  │  (генерация событий) │   │
│  │  агентов)    │  │   гильдии)   │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Day Simulator                          │   │
│  │  (цикл по дням: churn check → sessions → actions)         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Output Writer                             │
│              (JSONL / Parquet, батчевая запись)                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. Структура модулей

```
/idle_champions_simulator
│
├── /configs                     # Конфигурационные файлы
│   ├── default.yaml             # Базовый конфиг со всеми параметрами
│   └── /overrides               # Сценарии-оверрайды
│       ├── bad_traffic.yaml
│       ├── high_whale_ratio.yaml
│       ├── broken_economy.yaml
│       └── ...
│
├── /src                         # Исходный код
│   ├── __init__.py
│   ├── cli.py                   # CLI интерфейс (argparse)
│   ├── config.py                # Загрузка и валидация конфигов
│   ├── models.py                # Dataclasses (Agent, Event, etc.)
│   ├── simulation.py            # Основной движок симуляции
│   ├── agents.py                # Логика поведения агентов
│   ├── world.py                 # Состояние мира (баннеры, гильдии)
│   ├── events.py                # Генерация событий
│   ├── writers.py               # Запись в JSONL/Parquet
│   └── validators.py            # Валидация конфигов
│
├── /schemas                     # JSON Schema для валидации
│   └── config_schema.json
│
├── /output                      # Выходные данные (gitignored)
│   └── /run_20250201_123456
│       ├── events.jsonl
│       ├── events.parquet
│       └── metadata.json
│
├── /tests                       # Тесты
│   ├── test_config.py
│   ├── test_agents.py
│   ├── test_simulation.py
│   └── ...
│
├── requirements.txt
├── README.md
└── generate.py                  # Entry point
```

---

## 3. Конфигурация

### 3.1. Структура default.yaml

```yaml
# =============================================================================
# SIMULATION PARAMETERS
# =============================================================================
simulation:
  seed: 42                        # Random seed для воспроизводимости
  start_date: "2025-01-01"        # Дата начала симуляции
  duration_days: 90               # Длительность в днях
  
# =============================================================================
# INSTALL DISTRIBUTION
# =============================================================================
installs:
  total: 50000                    # Всего установок за период
  
  # Распределение по дням (daily installs)
  distribution: "decay"           # decay | uniform | custom
  decay_rate: 0.02                # Для decay: скорость затухания
  
  # Источники трафика
  sources:
    organic:
      share: 0.40
      retention_modifier: 1.0
      monetization_modifier: 1.0
    google_ads:
      share: 0.25
      retention_modifier: 0.9
      monetization_modifier: 1.1
    facebook:
      share: 0.20
      retention_modifier: 0.85
      monetization_modifier: 1.05
    unity_ads:
      share: 0.10
      retention_modifier: 0.75
      monetization_modifier: 0.8
    influencer:
      share: 0.05
      retention_modifier: 1.1
      monetization_modifier: 0.9

# =============================================================================
# PLAYER TYPES
# =============================================================================
player_types:
  whale:
    share: 0.003
    spending_monthly_usd: [100, 500]
    sessions_per_day: [3, 6]
    session_duration_min: [15, 45]
    retention:
      d1: 0.85
      d7: 0.70
      d30: 0.55
      d90: 0.40
    ad_watch_probability: 0.1
    gacha_desire: 0.7
    arena_engagement: 0.95
    guild_engagement: 0.90
    
  dolphin:
    share: 0.012
    spending_monthly_usd: [10, 100]
    sessions_per_day: [2, 4]
    session_duration_min: [10, 30]
    retention:
      d1: 0.70
      d7: 0.45
      d30: 0.25
      d90: 0.12
    ad_watch_probability: 0.4
    gacha_desire: 0.5
    arena_engagement: 0.80
    guild_engagement: 0.70
    
  minnow:
    share: 0.035
    spending_monthly_usd: [1, 15]
    sessions_per_day: [1, 3]
    session_duration_min: [5, 20]
    retention:
      d1: 0.55
      d7: 0.30
      d30: 0.12
      d90: 0.05
    ad_watch_probability: 0.6
    gacha_desire: 0.35
    arena_engagement: 0.60
    guild_engagement: 0.50
    
  free_engaged:
    share: 0.25
    spending_monthly_usd: [0, 0]
    sessions_per_day: [2, 4]
    session_duration_min: [10, 25]
    retention:
      d1: 0.50
      d7: 0.25
      d30: 0.10
      d90: 0.04
    ad_watch_probability: 0.85
    gacha_desire: 0.4
    arena_engagement: 0.70
    guild_engagement: 0.60
    
  free_casual:
    share: 0.45
    spending_monthly_usd: [0, 0]
    sessions_per_day: [0.3, 1.5]
    session_duration_min: [3, 12]
    retention:
      d1: 0.40
      d7: 0.15
      d30: 0.05
      d90: 0.02
    ad_watch_probability: 0.50
    gacha_desire: 0.2
    arena_engagement: 0.30
    guild_engagement: 0.20
    
  free_churner:
    share: 0.25
    spending_monthly_usd: [0, 0]
    sessions_per_day: [1, 2]
    session_duration_min: [2, 8]
    retention:
      d1: 0.25
      d7: 0.05
      d30: 0.01
      d90: 0.002
    ad_watch_probability: 0.30
    gacha_desire: 0.1
    arena_engagement: 0.10
    guild_engagement: 0.05

# =============================================================================
# ECONOMY
# =============================================================================
economy:
  # Начальные значения
  initial:
    gold: 1000
    gems: 100
    summon_tickets: 5
    energy: 120
    
  # Energy
  energy:
    max: 120
    regen_minutes: 5              # 1 energy per N minutes
    stage_cost: 6
    
  # Stage rewards (per stage, scales with chapter)
  stage_rewards:
    gold_base: 100
    gold_per_chapter: 50
    exp_base: 20
    exp_per_chapter: 10
    
  # Idle rewards (per hour, scales with max stage)
  idle_rewards:
    gold_per_hour_base: 500
    gold_per_stage_mult: 0.05
    max_hours: 12
    
  # Hero levelup costs
  hero_levelup:
    gold_base: 100
    gold_per_level_mult: 1.15     # Exponential growth

# =============================================================================
# GACHA
# =============================================================================
gacha:
  # Costs
  single_gems: 300
  multi_gems: 2700                # 10% discount for 10-pull
  
  # Rates
  rates:
    common: 0.60
    rare: 0.30
    epic: 0.08
    legendary: 0.02
    
  # Pity system
  pity:
    threshold: 90                 # Guaranteed legendary at 90
    soft_pity_start: 75           # Increased rates from 75
    soft_pity_rate_boost: 0.05    # +5% per pull after soft pity

# =============================================================================
# SHOP / IAP
# =============================================================================
shop:
  products:
    starter_pack:
      price_usd: 0.99
      gems: 500
      summon_tickets: 10
      limit: 1                    # One-time purchase
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
      
  # Ads
  ads:
    reward_gems: 50
    max_per_day: 5
    cooldown_minutes: 30

# =============================================================================
# VIP SYSTEM
# =============================================================================
vip:
  levels:
    0: { threshold: 0, energy_bonus: 0, gold_bonus: 0 }
    1: { threshold: 5, energy_bonus: 10, gold_bonus: 0 }
    2: { threshold: 15, energy_bonus: 10, gold_bonus: 0 }
    3: { threshold: 30, energy_bonus: 10, gold_bonus: 0.2 }
    4: { threshold: 50, energy_bonus: 10, gold_bonus: 0.2 }
    5: { threshold: 100, energy_bonus: 20, gold_bonus: 0.2 }
    6: { threshold: 200, energy_bonus: 20, gold_bonus: 0.2 }
    7: { threshold: 500, energy_bonus: 20, gold_bonus: 0.5 }
    8: { threshold: 1000, energy_bonus: 30, gold_bonus: 0.5 }
    9: { threshold: 2000, energy_bonus: 30, gold_bonus: 1.0 }
    10: { threshold: 5000, energy_bonus: 40, gold_bonus: 1.0 }

# =============================================================================
# PROGRESSION
# =============================================================================
progression:
  # Campaign
  chapters: 20
  stages_per_chapter: 10
  
  # Power requirements (base, scales exponentially)
  stage_power:
    base: 100
    per_stage_mult: 1.08
    
  # Player level
  player_level:
    max: 100
    exp_per_level_base: 100
    exp_per_level_mult: 1.12
    
  # Feature unlocks
  unlocks:
    gacha: 3
    daily_quests: 5
    events: 5
    arena: 10
    guild: 15

# =============================================================================
# HEROES
# =============================================================================
heroes:
  # Hero pool (simplified: ID pattern + count per rarity)
  pool:
    common: 20                    # hero_common_001 ... hero_common_020
    rare: 15                      # hero_rare_001 ... hero_rare_015
    epic: 10                      # hero_epic_001 ... hero_epic_010
    legendary: 5                  # hero_legendary_001 ... hero_legendary_005
    
  # Base power by rarity
  base_power:
    common: 50
    rare: 100
    epic: 200
    legendary: 400
    
  # Power scaling
  power_per_level: 10
  power_per_star_mult: 1.2        # Each star = 20% more power

# =============================================================================
# SOCIAL
# =============================================================================
social:
  # Arena
  arena:
    daily_attempts: 5
    attempt_cost_gems: 50
    rating_start: 1000
    rating_k_factor: 32           # ELO K-factor
    
  # Guilds
  guilds:
    count: 500                    # Number of guilds to simulate
    max_members: 30
    boss_daily_attempts: 1

# =============================================================================
# A/B TESTS
# =============================================================================
ab_tests:
  onboarding_length:
    enabled: true
    variants: ["control", "short", "extended"]
    weights: [0.33, 0.33, 0.34]
    effects:
      short:
        tutorial_steps: 4
        d1_retention_mult: 1.05
        d7_retention_mult: 0.92
      extended:
        tutorial_steps: 12
        d1_retention_mult: 0.97
        d7_retention_mult: 1.04
        
  starter_pack_price:
    enabled: true
    variants: ["control", "higher", "lower"]
    weights: [0.33, 0.33, 0.34]
    effects:
      higher:
        price_usd: 1.99
        conversion_mult: 0.60
      lower:
        price_usd: 0.49
        conversion_mult: 1.60
        
  gacha_pity_display:
    enabled: true
    variants: ["control", "visible"]
    weights: [0.50, 0.50]
    effects:
      visible:
        gacha_desire_mult_above_50_pity: 1.15
        
  energy_regen_rate:
    enabled: true
    variants: ["control", "fast", "slow"]
    weights: [0.33, 0.33, 0.34]
    effects:
      fast:
        regen_minutes: 4
        sessions_mult: 1.20
        energy_purchase_mult: 0.70
      slow:
        regen_minutes: 6
        sessions_mult: 0.85
        energy_purchase_mult: 1.25
        
  ad_reward_amount:
    enabled: true
    variants: ["control", "generous", "stingy"]
    weights: [0.33, 0.33, 0.34]
    effects:
      generous:
        reward_gems: 100
        ad_watch_mult: 1.40
        iap_conversion_mult: 0.90
      stingy:
        reward_gems: 25
        ad_watch_mult: 0.70
        iap_conversion_mult: 1.05
        
  late_game_offer:
    enabled: true
    variants: ["control", "discount_50", "bonus_hero"]
    weights: [0.33, 0.33, 0.34]
    activation_condition: "days_since_install >= 30"
    effects:
      discount_50:
        iap_conversion_mult: 1.25
      bonus_hero:
        iap_conversion_mult: 1.15
        d30_d60_retention_mult: 1.10

# =============================================================================
# SPECIAL SCENARIOS
# =============================================================================
scenarios:
  bad_traffic:
    enabled: true
    day: 25                       # Day of simulation
    source_name: "fake_network"
    volume: 2000
    retention_modifier: 0.3
    monetization_modifier: 0.1
    bot_ratio: 0.4                # 40% are bots

# =============================================================================
# OUTPUT
# =============================================================================
output:
  format: "jsonl"                 # jsonl | parquet | both
  compression: "gzip"             # none | gzip (for jsonl)
  batch_size: 10000               # Events per batch write
  include_metadata: true          # Generate metadata.json

# =============================================================================
# DEVICE SIMULATION
# =============================================================================
devices:
  platforms:
    ios: 0.45
    android: 0.55
    
  countries:
    RU: 0.40
    US: 0.15
    DE: 0.10
    BR: 0.10
    JP: 0.08
    KR: 0.07
    other: 0.10
    
  # Model pools (simplified)
  ios_models: ["iPhone 12", "iPhone 13", "iPhone 14", "iPhone 15", "iPad Air"]
  android_models: ["Samsung Galaxy S21", "Samsung Galaxy S22", "Pixel 6", "Pixel 7", "Xiaomi 12"]
  
  app_versions: ["1.0.0", "1.0.1", "1.1.0", "1.2.0"]
  app_version_weights: [0.05, 0.10, 0.25, 0.60]  # Most users on latest
```

### 3.2. Пример override файла

```yaml
# /configs/overrides/high_whale_ratio.yaml
# Сценарий: много китов (для изучения whale behavior)

player_types:
  whale:
    share: 0.01           # 1% вместо 0.3%
  dolphin:
    share: 0.03           # 3% вместо 1.2%
  minnow:
    share: 0.05           # 5% вместо 3.5%
  free_engaged:
    share: 0.25
  free_casual:
    share: 0.41           # Уменьшили чтобы сумма = 1
  free_churner:
    share: 0.25
```

### 3.3. Merge Logic

```python
def merge_configs(base: dict, override: dict) -> dict:
    """Deep merge override into base config."""
    result = copy.deepcopy(base)
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result
```

---

## 4. Валидация конфигов

### 4.1. Правила валидации

| Категория | Правило | Пример |
|-----------|---------|--------|
| Types | Поля имеют правильные типы | `seed` должен быть int |
| Ranges | Значения в допустимых диапазонах | `retention.d1` в [0, 1] |
| Sums | Суммы равны ожидаемым | `player_types.*.share` = 1.0 |
| References | Ссылки валидны | `unlocks.gacha` ≤ `player_level.max` |
| Logic | Логическая согласованность | `d1_retention` ≥ `d7_retention` ≥ `d30_retention` |

### 4.2. JSON Schema (упрощённый пример)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["simulation", "installs", "player_types"],
  "properties": {
    "simulation": {
      "type": "object",
      "required": ["seed", "start_date", "duration_days"],
      "properties": {
        "seed": { "type": "integer" },
        "start_date": { "type": "string", "format": "date" },
        "duration_days": { "type": "integer", "minimum": 1, "maximum": 365 }
      }
    },
    "player_types": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["share", "retention"],
        "properties": {
          "share": { "type": "number", "minimum": 0, "maximum": 1 },
          "retention": {
            "type": "object",
            "properties": {
              "d1": { "type": "number", "minimum": 0, "maximum": 1 },
              "d7": { "type": "number", "minimum": 0, "maximum": 1 },
              "d30": { "type": "number", "minimum": 0, "maximum": 1 }
            }
          }
        }
      }
    }
  }
}
```

### 4.3. Custom Validators

```python
class ConfigValidator:
    def validate(self, config: dict) -> list[str]:
        """Возвращает список ошибок (пустой = всё ок)."""
        errors = []
        
        # 1. JSON Schema validation
        errors.extend(self._validate_schema(config))
        
        # 2. Sum validations
        errors.extend(self._validate_shares_sum(config))
        
        # 3. Retention order
        errors.extend(self._validate_retention_order(config))
        
        # 4. Cross-references
        errors.extend(self._validate_references(config))
        
        return errors
    
    def _validate_shares_sum(self, config: dict) -> list[str]:
        errors = []
        
        # Player types sum = 1.0
        player_sum = sum(pt["share"] for pt in config["player_types"].values())
        if abs(player_sum - 1.0) > 0.001:
            errors.append(f"player_types shares sum to {player_sum}, expected 1.0")
        
        # Install sources sum = 1.0
        source_sum = sum(s["share"] for s in config["installs"]["sources"].values())
        if abs(source_sum - 1.0) > 0.001:
            errors.append(f"install sources shares sum to {source_sum}, expected 1.0")
        
        return errors
    
    def _validate_retention_order(self, config: dict) -> list[str]:
        errors = []
        
        for name, pt in config["player_types"].items():
            ret = pt["retention"]
            if not (ret["d1"] >= ret["d7"] >= ret["d30"] >= ret.get("d90", 0)):
                errors.append(f"player_type '{name}': retention must be d1 >= d7 >= d30 >= d90")
        
        return errors
```

---

## 5. CLI Interface

### 5.1. Команды

```bash
# Базовый запуск
python generate.py

# С кастомным конфигом
python generate.py --config configs/default.yaml

# С override
python generate.py --override configs/overrides/bad_traffic.yaml

# Несколько overrides (применяются последовательно)
python generate.py --override configs/overrides/high_whale_ratio.yaml \
                   --override configs/overrides/broken_economy.yaml

# Кастомный output
python generate.py --output ./my_output

# Только валидация (без генерации)
python generate.py --validate-only

# Verbose mode
python generate.py --verbose

# Указать seed (перезаписывает конфиг)
python generate.py --seed 12345

# Сухой запуск (показать параметры, не генерировать)
python generate.py --dry-run
```

### 5.2. Аргументы

| Аргумент | Короткий | По умолчанию | Описание |
|----------|----------|--------------|----------|
| `--config` | `-c` | `configs/default.yaml` | Базовый конфиг |
| `--override` | `-o` | None | Override файл(ы), можно несколько |
| `--output` | `-O` | `./output` | Папка для результатов |
| `--seed` | `-s` | из конфига | Перезаписать seed |
| `--validate-only` | `-v` | False | Только проверить конфиг |
| `--dry-run` | `-d` | False | Показать параметры без генерации |
| `--verbose` | | False | Подробный вывод |
| `--format` | `-f` | из конфига | Формат: jsonl, parquet, both |

### 5.3. Пример вывода

```
$ python generate.py --override configs/overrides/bad_traffic.yaml --verbose

╔══════════════════════════════════════════════════════════════════╗
║           Idle Champions: Synthetic Data Generator               ║
╚══════════════════════════════════════════════════════════════════╝

[CONFIG] Loading configs...
  ✓ Base: configs/default.yaml
  ✓ Override: configs/overrides/bad_traffic.yaml

[VALIDATE] Validating configuration...
  ✓ Schema validation passed
  ✓ Share sums validated
  ✓ Retention order validated
  ✓ All validations passed

[PARAMS] Simulation parameters:
  • Seed: 42
  • Start date: 2025-01-01
  • Duration: 90 days
  • Total installs: 50,000
  • Bad traffic: Day 25, 2,000 installs

[GENERATE] Starting simulation...
  Day 1/90: 1,247 installs, 15,832 events [00:02]
  Day 2/90: 1,221 installs, 28,451 events [00:05]
  ...
  Day 90/90: 312 installs, 892,441 events [03:45]

[OUTPUT] Writing results...
  ✓ events.jsonl.gz (1.2 GB, 42,847,293 events)
  ✓ metadata.json

[DONE] Completed in 3m 52s
  Output: ./output/run_20250201_143052/
```

---

## 6. Output Format

### 6.1. JSONL (events.jsonl.gz)

Каждая строка — одно событие в JSON:

```json
{"event_id":"evt_00001","event_name":"session_start","event_timestamp":"2025-01-01T08:23:15.123Z","user_id":"u_00001",...}
{"event_id":"evt_00002","event_name":"tutorial_step","event_timestamp":"2025-01-01T08:23:20.456Z","user_id":"u_00001",...}
```

### 6.2. Parquet (events.parquet)

Колоночный формат, оптимизирован для аналитики:

| Колонка | Тип | Описание |
|---------|-----|----------|
| event_id | STRING | UUID события |
| event_name | STRING | Название события |
| event_timestamp | TIMESTAMP | Время события |
| user_id | STRING | ID игрока |
| session_id | STRING | ID сессии |
| device_id | STRING | ID устройства |
| platform | STRING | ios/android |
| country | STRING | Страна |
| app_version | STRING | Версия приложения |
| player_level | INT32 | Уровень игрока |
| vip_level | INT32 | VIP уровень |
| total_spent_usd | FLOAT | Всего потрачено |
| days_since_install | INT32 | Дней с установки |
| cohort_date | DATE | Дата когорты |
| ab_tests | MAP<STRING,STRING> | A/B тесты |
| event_properties | STRING (JSON) | Свойства события |

### 6.3. Metadata (metadata.json)

```json
{
  "generator_version": "0.1.0",
  "generated_at": "2025-02-01T14:30:52Z",
  "config_hash": "sha256:abc123...",
  "seed": 42,
  "simulation": {
    "start_date": "2025-01-01",
    "end_date": "2025-03-31",
    "duration_days": 90
  },
  "stats": {
    "total_installs": 52000,
    "total_events": 42847293,
    "unique_users": 52000,
    "events_by_type": {
      "session_start": 1523847,
      "session_end": 1523102,
      "stage_complete": 8234521,
      ...
    },
    "installs_by_source": {
      "organic": 20800,
      "google_ads": 13000,
      ...
    },
    "installs_by_player_type": {
      "whale": 156,
      "dolphin": 624,
      ...
    }
  },
  "config_snapshot": { ... }
}
```

---

## 7. Dependencies

### 7.1. requirements.txt

```
# Core
pyyaml>=6.0
pydantic>=2.0
jsonschema>=4.0

# Data processing
numpy>=1.24
pandas>=2.0
pyarrow>=14.0

# CLI
click>=8.0
rich>=13.0           # Pretty console output

# Testing
pytest>=7.0
pytest-cov>=4.0

# Dev
black>=23.0
ruff>=0.1.0
mypy>=1.0
```

### 7.2. Python Version

- Минимум: Python 3.10
- Рекомендуется: Python 3.11+

---

## 8. Performance Considerations

### 8.1. Оценка объёмов

| Параметр | Значение |
|----------|----------|
| Игроков | 50,000 |
| Дней | 90 |
| Событий/активный игрок/день | ~50–200 |
| Активных игроков (в среднем) | ~5,000–10,000 |
| Событий всего | ~20–50M |
| Размер события (JSON) | ~500–1000 bytes |
| Размер данных (raw) | ~15–40 GB |
| Размер данных (gzip) | ~1–3 GB |
| Размер данных (parquet) | ~2–5 GB |

### 8.2. Оптимизации

1. **Батчевая запись** — пишем по 10K событий, не по одному
2. **Streaming** — не держим все события в памяти
3. **Предварительная генерация** — герои, гильдии создаются один раз
4. **NumPy для random** — быстрее чем стандартный random

### 8.3. Прогресс и время

- Ожидаемое время генерации: **3–10 минут** на типичном ноутбуке
- Progress bar с ETA

---

## 9. Testing Strategy

### 9.1. Unit Tests

- Config loading и validation
- Individual agent behaviors
- Event generation
- Probability distributions

### 9.2. Integration Tests

- Full simulation run (small scale: 100 users, 7 days)
- Output format validation
- Determinism check (same seed = same output)

### 9.3. Smoke Tests

- Default config generates without errors
- All override scenarios work
- Output loads in ClickHouse

---

## 10. Future Enhancements (Out of Scope for v1)

- Real-time streaming генерация
- Web UI для конфигурации
- Встроенная загрузка в ClickHouse
- Параллельная генерация (multiprocessing)
- Плагинная архитектура для кастомных событий

---

## 11. Infrastructure & Deployment

### 11.1. Архитектура деплоя

```
┌──────────────────────────────────────────────────────────────────┐
│                         Server (Docker Compose)                   │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │   generator     │  │   clickhouse    │  │    superset     │   │
│  │   (Python)      │──▶│   (Database)    │◀──│   (BI Tool)     │   │
│  │   Port: -       │  │   Port: 8123    │  │   Port: 8088    │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
│          │                    ▲                                   │
│          ▼                    │                                   │
│  ┌────────────────────────────┴──────────────────────────────┐   │
│  │                   Shared Volume (/data)                    │   │
│  │   /data/configs/          - конфигурации                   │   │
│  │   /data/output/           - сгенерированные данные         │   │
│  │   /data/logs/             - логи генератора                │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                   Студенты подключаются через браузер:
                   - Superset: http://server:8088
                   - ClickHouse HTTP: http://server:8123
```

### 11.2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  generator:
    build: ./generator
    volumes:
      - ./data:/data
    environment:
      - CLICKHOUSE_HOST=clickhouse
      - CLICKHOUSE_PORT=9000
    depends_on:
      - clickhouse

  clickhouse:
    image: clickhouse/clickhouse-server:24.1
    ports:
      - "8123:8123"   # HTTP interface
      - "9000:9000"   # Native interface
    volumes:
      - ./data/clickhouse:/var/lib/clickhouse
      - ./clickhouse/init:/docker-entrypoint-initdb.d
    environment:
      - CLICKHOUSE_DB=idle_champions
      - CLICKHOUSE_USER=admin
      - CLICKHOUSE_PASSWORD=admin123

  superset:
    image: apache/superset:3.1.0
    ports:
      - "8088:8088"
    volumes:
      - ./data/superset:/app/superset_home
    environment:
      - SUPERSET_SECRET_KEY=your-secret-key
    depends_on:
      - clickhouse

volumes:
  clickhouse_data:
  superset_data:
```

### 11.3. Workflow преподавателя

```bash
# 1. Запустить инфраструктуру
docker-compose up -d clickhouse superset

# 2. Сгенерировать данные
docker-compose run generator python generate.py \
  --override /data/configs/overrides/scenario_week1.yaml

# 3. Данные автоматически загружены в ClickHouse
# 4. Студенты работают в Superset
```

### 11.4. Auto-load в ClickHouse

После генерации данные автоматически загружаются:

```python
# В конце generate.py
if config.output.auto_load_clickhouse:
    load_to_clickhouse(
        parquet_path=output_path / "events.parquet",
        table_name=f"events_{run_id}",
        clickhouse_host=os.environ.get("CLICKHOUSE_HOST", "localhost")
    )
```

---

## 12. Logging

### 12.1. Конфигурация

```python
# src/logging_config.py
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(output_dir: Path, verbose: bool = False):
    """Настройка логирования в консоль и файл."""
    
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Формат
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (rich formatting)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler
    log_file = output_dir / "logs" / f"generate_{datetime.now():%Y%m%d_%H%M%S}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Всегда подробно в файл
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return log_file
```

### 12.2. Уровни логирования

| Уровень | Что логируем |
|---------|--------------|
| DEBUG | Детали каждого агента, каждого дня |
| INFO | Прогресс по дням, итоговая статистика |
| WARNING | Подозрительные значения в конфиге |
| ERROR | Ошибки валидации, исключения |

### 12.3. Пример лога

```
2025-02-01 14:30:52 | INFO     | config   | Loaded base config: configs/default.yaml
2025-02-01 14:30:52 | INFO     | config   | Applied override: configs/overrides/bad_traffic.yaml
2025-02-01 14:30:52 | INFO     | validate | All validations passed
2025-02-01 14:30:52 | INFO     | generate | Starting simulation: 90 days, 50000 installs
2025-02-01 14:30:53 | INFO     | generate | Day 1: 1247 installs, 15832 events
2025-02-01 14:30:54 | DEBUG    | agents   | Agent u_00001 (whale): 4 sessions, spent $4.99
2025-02-01 14:30:55 | INFO     | generate | Day 2: 1221 installs, 28451 events
...
2025-02-01 14:34:45 | INFO     | output   | Written 42847293 events to events.parquet
2025-02-01 14:34:46 | INFO     | clickhouse | Loading data to table events_run_20250201_143052
2025-02-01 14:34:52 | INFO     | clickhouse | Load complete: 42847293 rows
2025-02-01 14:34:52 | INFO     | generate | Done in 3m 52s
```

---

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 0.1 | 2025-02-01 | Первый драфт. Добавлены: Docker Compose, auto-load ClickHouse, logging. |
