# Архитектура генератора

Описание модулей, их взаимодействия и внутренней логики симуляции.

## Содержание

- [Высокоуровневая схема](#высокоуровневая-схема)
- [Модули](#модули)
  - [config.py](#configpy)
  - [validators.py](#validatorspy)
  - [models.py](#modelspy)
  - [world.py](#worldpy)
  - [agents.py](#agentspy)
  - [events.py](#eventspy)
  - [simulation.py](#simulationpy)
  - [writers.py](#writerspy)
  - [cli.py](#clipy)
- [Поток данных](#поток-данных)
- [Модель поведения агентов](#модель-поведения-агентов)
- [Расширение функциональности](#расширение-функциональности)

---

## Высокоуровневая схема

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

---

## Модули

### config.py

**Назначение:** Загрузка и объединение YAML конфигураций.

**Ключевые компоненты:**

```python
def load_yaml(path: Path) -> dict
    """Загрузка одного YAML файла."""

def deep_merge(base: dict, override: dict) -> dict
    """Глубокое слияние конфигов (override перезаписывает base)."""

def load_config(base_path: Path, override_paths: list[Path]) -> dict
    """Загрузка базового конфига и применение overrides."""

class SimulationConfig:
    """Обёртка над dict с типизированным доступом к параметрам."""
```

**Пример использования:**

```python
from src.config import load_config, SimulationConfig

config_dict = load_config(
    Path("configs/default.yaml"),
    [Path("configs/overrides/bad_traffic.yaml")]
)
config = SimulationConfig(config_dict)

print(config.seed)  # 42
print(config.total_installs)  # 50000
```

---

### validators.py

**Назначение:** Валидация конфигурации перед запуском.

**Проверки:**

| Категория | Правило |
|-----------|---------|
| Required | Все обязательные секции присутствуют |
| Types | Поля имеют правильные типы |
| Ranges | Значения в допустимых диапазонах |
| Sums | `player_types.*.share` = 1.0, `sources.*.share` = 1.0 |
| Order | `d1_retention` ≥ `d7_retention` ≥ `d30_retention` |
| References | `unlocks.gacha` ≤ `player_level.max` |

**Использование:**

```python
from src.validators import validate_config, ValidationError

errors = validate_config(config_dict)
if errors:
    print("Validation failed:", errors)
```

---

### models.py

**Назначение:** Dataclasses для всех сущностей.

**Основные классы:**

```python
@dataclass
class AgentState:
    """Полное состояние игрока-агента."""
    user_id: str
    device_id: str
    agent_type: PlayerType
    install_date: date
    # ... 50+ полей состояния

@dataclass
class Event:
    """Структура события."""
    event_id: str
    event_name: str
    event_timestamp: datetime
    user_id: str
    session_id: str
    device: DeviceInfo
    user_properties: UserProperties
    ab_tests: dict[str, str]
    event_properties: dict

@dataclass
class HeroTemplate:
    """Шаблон героя (статичные данные)."""

@dataclass
class HeroInstance:
    """Экземпляр героя у игрока."""

@dataclass
class Guild:
    """Гильдия."""

@dataclass
class GachaBanner:
    """Баннер гачи."""
```

**Enums:**

```python
class PlayerType(Enum):
    WHALE, DOLPHIN, MINNOW, FREE_ENGAGED, FREE_CASUAL, FREE_CHURNER

class HeroRarity(Enum):
    COMMON, RARE, EPIC, LEGENDARY

class HeroClass(Enum):
    WARRIOR, MAGE, ARCHER, HEALER, TANK

class Platform(Enum):
    IOS, ANDROID
```

---

### world.py

**Назначение:** Глобальное состояние игрового мира.

**Класс WorldState:**

```python
@dataclass
class WorldState:
    config: SimulationConfig
    current_date: date
    day_number: int

    hero_templates: dict[str, HeroTemplate]  # Все шаблоны героев
    guilds: list[Guild]                      # Все гильдии
    banners: list[GachaBanner]               # Все баннеры гачи
    game_events: list[GameEvent]             # Временные события
```

**Методы:**

```python
@classmethod
def initialize(cls, config, rng) -> WorldState:
    """Инициализация мира: генерация героев, гильдий, баннеров."""

def advance_day(self):
    """Переход к следующему дню (сброс HP боссов и т.д.)."""

def get_active_banners(self) -> list[GachaBanner]:
    """Активные баннеры на текущую дату."""

def get_stage_power_requirement(self, chapter, stage) -> int:
    """Требование силы для прохождения уровня."""

def get_stage_rewards(self, chapter, stage) -> dict:
    """Награды за прохождение уровня."""

def get_idle_rewards(self, max_stage, hours) -> dict:
    """Idle награды за время офлайн."""
```

---

### agents.py

**Назначение:** Создание агентов и моделирование их поведения.

**AgentFactory:**

```python
class AgentFactory:
    """Фабрика создания агентов."""

    def create_agent(
        self,
        install_date: date,
        install_source: str,
        rng: Random,
        is_bot: bool = False
    ) -> AgentState:
        """Создаёт нового агента с начальными параметрами."""
```

**AgentBehavior:**

```python
class AgentBehavior:
    """Модель поведения агентов."""

    def get_retention_probability(self, agent, day) -> float:
        """Вероятность что агент вернётся на день N."""

    def will_return_today(self, agent, date, rng) -> bool:
        """Решение о возврате сегодня."""

    def get_sessions_count(self, agent, date, rng) -> int:
        """Количество сессий на сегодня."""

    def get_session_duration_minutes(self, agent, session_num, rng) -> int:
        """Длительность сессии в минутах."""

    def should_do_gacha(self, agent, rng) -> bool:
        """Решение делать ли гачу."""

    def roll_gacha(self, agent, rng) -> HeroRarity:
        """Рол гачи с учётом pity."""

    def should_attempt_iap(self, agent, trigger, rng) -> bool:
        """Решение о покупке."""

    # ... и другие методы решений
```

**A/B распределение:**

```python
def get_ab_group(user_id, test_name, variants, weights, seed) -> str:
    """Детерминированное распределение по группам A/B теста."""
```

---

### events.py

**Назначение:** Генерация 36 типов событий.

**EventEmitter:**

```python
class EventEmitter:
    """Генератор событий."""

    events: list[Event]  # Буфер событий

    def clear(self):
        """Очистить буфер."""

    def get_events(self) -> list[Event]:
        """Получить все события из буфера."""

    # 36 методов emit_*:
    def emit_session_start(self, agent, timestamp, ...) -> Event
    def emit_session_end(self, agent, timestamp, ...) -> Event
    def emit_economy_source(self, agent, timestamp, ...) -> Event
    def emit_stage_complete(self, agent, timestamp, ...) -> Event
    def emit_gacha_summon(self, agent, timestamp, ...) -> Event
    def emit_iap_purchase(self, agent, timestamp, ...) -> Event
    # ... и т.д.
```

---

### simulation.py

**Назначение:** Основной движок симуляции.

**Simulator:**

```python
class Simulator:
    """Движок симуляции."""

    def __init__(self, config, output_manager, progress_callback=None):
        self.config = config
        self.output = output_manager
        self.rng = Random(config.seed)
        self.world = None
        self.state = SimulationState()

    def run(self):
        """Запуск полной симуляции."""
        self._initialize()
        self._calculate_install_distribution()

        for day in range(duration):
            self._simulate_day()
            self.world.advance_day()
```

**Алгоритм симуляции дня:**

```python
def _simulate_day(self):
    # 1. Создать новые установки
    self._create_daily_installs()

    # 2. Для каждого активного агента
    for agent in self.state.agents:
        if agent.is_churned:
            continue

        if self.behavior.will_return_today(agent, date, rng):
            self._simulate_agent_day(agent)
        else:
            # Проверить окончательный churn
            ...
```

**Алгоритм симуляции сессии:**

```python
def _simulate_session(self, agent, start_time, session_number):
    # 1. Emit session_start
    # 2. Если первая сессия дня:
    #    - Claim idle rewards
    #    - Claim daily login
    #    - Claim monthly pass
    # 3. Основной цикл действий:
    #    - Play stages
    #    - Upgrade heroes
    #    - Do gacha
    #    - Arena battles
    #    - Guild boss
    #    - Watch ads
    #    - Browse shop / IAP
    # 4. Emit session_end
```

---

### writers.py

**Назначение:** Запись данных в JSONL и Parquet.

**JSONLWriter:**

```python
class JSONLWriter:
    """Запись событий в JSONL формат."""

    def write_event(self, event: Event):
        """Добавить событие в буфер."""

    def _flush(self):
        """Записать буфер в файл."""
```

**ParquetWriter:**

```python
class ParquetWriter:
    """Запись событий в Parquet формат."""

    SCHEMA = pa.schema([...])  # Плоская схема

    def write_event(self, event: Event):
        """Преобразовать и записать событие."""
```

**OutputManager:**

```python
class OutputManager:
    """Управление всеми writers."""

    def write_event(self, event):
        """Записать во все активные writers."""

    def write_events(self, events):
        """Записать список событий."""

    def finalize(self, end_date, generation_time):
        """Завершить и записать metadata."""
```

---

### cli.py

**Назначение:** Интерфейс командной строки.

**Использует:**
- `click` для парсинга аргументов
- `rich` для красивого вывода

**Команды:**

```bash
python generate.py [OPTIONS]

Options:
  -c, --config PATH       Base configuration file
  -o, --override PATH     Override file(s), can be used multiple times
  -O, --output PATH       Output directory
  -s, --seed INTEGER      Override random seed
  -v, --validate-only     Only validate configuration
  -d, --dry-run           Show parameters without generating
  -f, --format TEXT       Output format: jsonl, parquet, both
  --verbose               Verbose output
  --help                  Show this message and exit
```

---

## Поток данных

```
1. CLI парсит аргументы
   │
   ▼
2. load_config() загружает YAML
   │
   ▼
3. validate_config() проверяет конфиг
   │
   ▼
4. SimulationConfig оборачивает dict
   │
   ▼
5. OutputManager открывает writers
   │
   ▼
6. Simulator.run():
   │
   ├─► WorldState.initialize()
   │   - Генерация hero_templates
   │   - Генерация guilds
   │   - Генерация banners
   │
   ├─► _calculate_install_distribution()
   │   - Расчёт установок по дням
   │
   └─► for day in range(duration):
       │
       ├─► _create_daily_installs()
       │   - AgentFactory.create_agent()
       │   - _simulate_first_session()
       │
       └─► for agent in agents:
           │
           └─► _simulate_agent_day()
               │
               └─► for session in sessions:
                   │
                   ├─► EventEmitter.emit_*()
                   │
                   └─► OutputManager.write_events()
   │
   ▼
7. OutputManager.finalize()
   - Запись metadata.json
```

---

## Модель поведения агентов

### Retention

Двухфазная экспоненциальная модель:

```python
if day <= 7:
    # Фаза 1: быстрый отсев
    decay_rate = early_decay
else:
    # Фаза 2: стабилизация
    decay_rate = late_decay

retention = d1_retention * exp(-decay_rate * (day - 1))
```

**Модификаторы:**
- Источник трафика (×0.75 - ×1.1)
- A/B тесты
- Негативный опыт (consecutive_losses > 3 → ×0.85)
- Позитивный опыт (got_legendary → ×1.15)
- Гильдия (×1.10)
- Бот (×0.3)

### Сессии

Распределение времени входа:

| Период | Доля |
|--------|------|
| 00:00–07:00 | 5% |
| 07:00–09:00 | 15% |
| 09:00–12:00 | 10% |
| 12:00–14:00 | 20% |
| 14:00–18:00 | 10% |
| 18:00–21:00 | 25% |
| 21:00–24:00 | 15% |

### Gacha

```python
# Soft pity (с 75 призыва)
if pity >= soft_pity_start:
    legendary_rate += (pity - soft_pity_start + 1) * 0.05

# Hard pity (90 призыв)
if pity >= threshold - 1:
    return LEGENDARY
```

### IAP

Триггеры покупки:
- `starter_pack_offer` → 15% base
- `out_of_gems_gacha` → 8%
- `pity_close` → 12%
- `monthly_pass_reminder` → 20%

Множители по типу игрока:
- whale: ×3.0
- dolphin: ×1.5
- minnow: ×0.8
- free: ×0.02-0.1

---

## Расширение функциональности

### Добавление нового типа события

1. Добавить метод `emit_*` в `events.py`:

```python
def emit_my_new_event(self, agent, timestamp, ...):
    return self._create_event(
        "my_new_event",
        timestamp,
        agent,
        current_date,
        {
            "field1": value1,
            "field2": value2,
        },
    )
```

2. Вызвать из `simulation.py` в нужном месте.

### Добавление нового поведения агента

1. Добавить метод решения в `agents.py`:

```python
def should_do_something(self, agent, rng) -> bool:
    base_prob = 0.5
    # модификаторы...
    return rng.random() < base_prob
```

2. Добавить обработку в `simulation.py`.

### Добавление нового A/B теста

1. Добавить в `configs/default.yaml`:

```yaml
ab_tests:
  my_test:
    enabled: true
    variants: ["control", "variant_a"]
    weights: [0.5, 0.5]
    effects:
      variant_a:
        some_modifier: 1.2
```

2. Учесть эффект в соответствующем методе `agents.py`.
