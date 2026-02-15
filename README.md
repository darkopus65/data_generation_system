# Idle Champions: Synthetic

Генератор синтетических данных игровой аналитики для учебного курса "Приложения и методы анализа данных в компьютерных играх".

## Описание

Симулятор генерирует реалистичные event-логи мобильной F2P игры жанра Idle RPG + Gacha. Данные подходят для практики:
- Анализа retention, конверсии, LTV
- Построения воронок и когортного анализа
- Оценки A/B тестов
- Выявления аномалий (плохой трафик)

## Быстрый старт

### Установка

```bash
# Клонировать репозиторий
cd data_generation_system

# Установить зависимости
pip install -r requirements.txt
```

### Запуск

```bash
# Базовый запуск (50K игроков, 90 дней, ~20-50M событий)
python generate.py

# Быстрый тест (500 игроков, 7 дней, ~70K событий)
python generate.py --override configs/overrides/small_test.yaml

# С кастомным сценарием
python generate.py --override configs/overrides/bad_traffic.yaml

# Только валидация конфига
python generate.py --validate-only

# Справка по параметрам
python generate.py --help
```

### Параметры CLI

| Параметр | Короткий | По умолчанию | Описание |
|----------|----------|--------------|----------|
| `--config` | `-c` | `configs/default.yaml` | Базовый конфиг |
| `--override` | `-o` | — | Override файл(ы), можно несколько |
| `--output` | `-O` | `./output` | Папка для результатов |
| `--seed` | `-s` | из конфига | Перезаписать seed |
| `--validate-only` | `-v` | False | Только проверить конфиг |
| `--dry-run` | `-d` | False | Показать параметры без генерации |
| `--format` | `-f` | из конфига | Формат: jsonl, parquet, both |
| `--verbose` | — | False | Подробный вывод |

## Выходные данные

После запуска в папке `output/run_YYYYMMDD_HHMMSS/` появятся:

### events.jsonl.gz

Event-лог в формате JSONL (одно событие на строку, сжатый gzip):

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440001",
  "event_name": "session_start",
  "event_timestamp": "2025-01-15T14:00:00.000Z",
  "user_id": "u_000001",
  "session_id": "s_abc001",
  "device": {
    "device_id": "d_000001",
    "platform": "ios",
    "os_version": "17.2",
    "app_version": "1.2.0",
    "device_model": "iPhone 14",
    "country": "RU",
    "language": "ru"
  },
  "user_properties": {
    "player_level": 25,
    "vip_level": 2,
    "total_spent_usd": 14.99,
    "days_since_install": 12,
    "cohort_date": "2025-01-03",
    "current_chapter": 5
  },
  "ab_tests": {
    "onboarding_length": "control",
    "starter_pack_price": "lower"
  },
  "event_properties": {
    "session_number": 47,
    "is_first_session": false,
    "time_since_last_session_sec": 28800,
    "install_source": "organic"
  }
}
```

### events.parquet

Тот же лог в колоночном формате Parquet (эффективнее для аналитики).

### metadata.json

Метаданные запуска со статистикой:

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
    "events_by_type": { ... },
    "installs_by_source": { ... },
    "installs_by_player_type": { ... }
  }
}
```

## Структура проекта

```
data_generation_system/
├── configs/
│   ├── default.yaml              # Базовая конфигурация
│   └── overrides/                # Сценарии-оверрайды
│       ├── bad_traffic.yaml      # Плохой трафик на день 25
│       ├── high_whale_ratio.yaml # Больше платящих игроков
│       └── small_test.yaml       # Для быстрого тестирования
├── src/
│   ├── models.py                 # Dataclasses (Agent, Event, Hero)
│   ├── config.py                 # Загрузка и merge конфигов
│   ├── validators.py             # Валидация конфигурации
│   ├── world.py                  # Состояние мира (герои, гильдии)
│   ├── agents.py                 # Модель поведения агентов
│   ├── events.py                 # Генерация 36 типов событий
│   ├── writers.py                # Запись JSONL/Parquet
│   ├── simulation.py             # Основной движок симуляции
│   └── cli.py                    # CLI интерфейс
├── infrastructure/               # Docker инфраструктура
│   ├── docker-compose.yml        # ClickHouse + Superset
│   ├── clickhouse/               # Конфиги и init скрипты CH
│   ├── superset/                 # Конфиг Superset
│   └── README.md                 # Инструкция по развёртыванию
├── scripts/
│   ├── load_to_clickhouse.py     # Загрузка данных в ClickHouse
│   └── setup_teams.py            # Настройка командных баз
├── tests/                        # Юнит-тесты
├── docs/                         # Спецификации (GDD, Event Taxonomy)
├── output/                       # Результаты генерации (gitignored)
├── generate.py                   # Entry point
└── requirements.txt
```

## Ключевые особенности

### Детерминированность

Один и тот же seed всегда даёт идентичные данные:

```bash
python generate.py --seed 42
python generate.py --seed 42  # Тот же результат
```

### Типы игроков

| Тип | Доля | Описание |
|-----|------|----------|
| `whale` | 0.3% | Тратят $100+/мес, высокая активность |
| `dolphin` | 1.2% | Тратят $10-100/мес |
| `minnow` | 3.5% | Мелкие траты <$10 |
| `free_engaged` | 25% | Активные F2P, смотрят рекламу |
| `free_casual` | 45% | Нерегулярные F2P |
| `free_churner` | 25% | Быстро уходят (D1-D3 churn) |

### A/B тесты

6 предзаданных тестов с реалистичными эффектами:
- `onboarding_length` — длина туториала
- `starter_pack_price` — цена стартового пакета
- `gacha_pity_display` — показ счётчика pity
- `energy_regen_rate` — скорость регенерации энергии
- `ad_reward_amount` — награда за рекламу
- `late_game_offer` — предложение для игроков D30+

### Сценарий "Плохой трафик"

На день 25 симулируется закупка некачественного трафика:
- 2000 установок из `fake_network`
- 40% ботов
- Retention ×0.3, монетизация ×0.1

## Интеграция с Apache Superset

Для развёртывания полной аналитической системы (ClickHouse + Superset):

```bash
# 1. Запуск инфраструктуры
cd infrastructure
docker-compose up -d

# 2. Генерация данных
cd ..
python generate.py --seed 42

# 3. Загрузка в ClickHouse
pip install clickhouse-connect
python scripts/load_to_clickhouse.py --input output/run_*/events.jsonl.gz --run-id baseline

# 4. Открыть Superset
# http://localhost:8088 (admin / admin123)
```

Подробнее: [infrastructure/README.md](infrastructure/README.md)

## Документация

- [Конфигурация](docs/gen/CONFIGURATION.md) — все параметры конфига
- [A/B тесты](docs/gen/AB_TESTS.md) — описание тестов и эффектов
- [Архитектура](docs/gen/ARCHITECTURE.md) — модули и их взаимодействие
- [События](docs/gen/EVENTS_REFERENCE.md) — справочник по 36 типам событий
- [GDD](docs/GDD_v0.2.md) — Game Design Document
- [Event Taxonomy](docs/EVENT_TAXONOMY_v0.2.md) — полная схема событий

## Требования

- Python 3.10+
- ~4-8 GB RAM для полной симуляции
- ~1-5 GB свободного места для output

## Лицензия

Учебный проект для курса "Приложения и методы анализа данных в компьютерных играх".
