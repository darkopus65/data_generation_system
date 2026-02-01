# Agent Behavior Model v0.1
## "Idle Champions: Synthetic"

**Статус:** Утверждён  
**Дата:** 2025-02-01  
**Связан с:** GDD v0.2, Event Taxonomy v0.2, AB_TESTS_CONFIG v0.1

---

## 1. Общая концепция

Агент — это симуляция одного игрока. Каждый агент имеет:
- **Профиль** — статические характеристики (тип, платёжеспособность, страна)
- **Состояние** — динамические данные (уровень, валюты, герои, прогресс)
- **Поведенческую модель** — вероятности действий в каждый момент времени

**Принципы симуляции:**
- Детерминированность через seed (воспроизводимость)
- Реалистичные распределения (retention, платежи, активность)
- Учёт A/B тестов (модификаторы поведения)
- Внутренняя согласованность (агент не тратит то, чего нет)

---

## 2. Типы агентов (Player Archetypes)

### 2.1. Распределение по типам

| Тип | Доля | Описание |
|-----|------|----------|
| `whale` | 0.3% | Тратят много ($100+), высокая активность |
| `dolphin` | 1.2% | Умеренные траты ($10–100), регулярная активность |
| `minnow` | 3.5% | Мелкие траты (<$10), часто только starter pack |
| `free_engaged` | 25% | Не платят, но активно играют, смотрят рекламу |
| `free_casual` | 45% | Не платят, играют нерегулярно |
| `free_churner` | 25% | Не платят, быстро уходят (D1-D3 churn) |

### 2.2. Характеристики по типам

#### Whale
```python
whale = {
    "spending_monthly_usd": (100, 500),      # диапазон трат в месяц
    "sessions_per_day": (3, 6),               # сессий в день
    "session_duration_min": (15, 45),         # минут за сессию
    "d1_retention": 0.85,
    "d7_retention": 0.70,
    "d30_retention": 0.55,
    "ad_watch_probability": 0.1,              # редко смотрят рекламу
    "gacha_pulls_per_week": (20, 100),
    "arena_engagement": 0.95,
    "guild_engagement": 0.90,
}
```

#### Dolphin
```python
dolphin = {
    "spending_monthly_usd": (10, 100),
    "sessions_per_day": (2, 4),
    "session_duration_min": (10, 30),
    "d1_retention": 0.70,
    "d7_retention": 0.45,
    "d30_retention": 0.25,
    "ad_watch_probability": 0.4,
    "gacha_pulls_per_week": (5, 30),
    "arena_engagement": 0.80,
    "guild_engagement": 0.70,
}
```

#### Minnow
```python
minnow = {
    "spending_monthly_usd": (1, 15),
    "sessions_per_day": (1, 3),
    "session_duration_min": (5, 20),
    "d1_retention": 0.55,
    "d7_retention": 0.30,
    "d30_retention": 0.12,
    "ad_watch_probability": 0.6,
    "gacha_pulls_per_week": (2, 10),
    "arena_engagement": 0.60,
    "guild_engagement": 0.50,
}
```

#### Free Engaged
```python
free_engaged = {
    "spending_monthly_usd": (0, 0),
    "sessions_per_day": (2, 4),
    "session_duration_min": (10, 25),
    "d1_retention": 0.50,
    "d7_retention": 0.25,
    "d30_retention": 0.10,
    "ad_watch_probability": 0.85,
    "gacha_pulls_per_week": (3, 15),          # только бесплатные
    "arena_engagement": 0.70,
    "guild_engagement": 0.60,
}
```

#### Free Casual
```python
free_casual = {
    "spending_monthly_usd": (0, 0),
    "sessions_per_day": (0.3, 1.5),           # не каждый день
    "session_duration_min": (3, 12),
    "d1_retention": 0.40,
    "d7_retention": 0.15,
    "d30_retention": 0.05,
    "ad_watch_probability": 0.50,
    "gacha_pulls_per_week": (1, 5),
    "arena_engagement": 0.30,
    "guild_engagement": 0.20,
}
```

#### Free Churner
```python
free_churner = {
    "spending_monthly_usd": (0, 0),
    "sessions_per_day": (1, 2),
    "session_duration_min": (2, 8),
    "d1_retention": 0.25,
    "d7_retention": 0.05,
    "d30_retention": 0.01,
    "ad_watch_probability": 0.30,
    "gacha_pulls_per_week": (0, 2),
    "arena_engagement": 0.10,
    "guild_engagement": 0.05,
}
```

---

## 3. Retention Model

### 3.1. Базовая кривая retention

Используем экспоненциальное затухание с модификаторами:

```python
def base_retention_probability(day: int, agent_type: str) -> float:
    """Вероятность что игрок ещё активен на день N."""
    params = RETENTION_PARAMS[agent_type]
    
    # Двухфазная модель: быстрый churn в начале, медленный потом
    if day <= 7:
        # Фаза 1: быстрый отсев
        decay_rate = params["early_decay"]
    else:
        # Фаза 2: стабилизация
        decay_rate = params["late_decay"]
    
    base_retention = params["d1_retention"] * math.exp(-decay_rate * (day - 1))
    return max(base_retention, params["floor"])  # минимальный порог
```

### 3.2. Retention параметры по типам

| Тип | D1 | D7 | D30 | D90 | Early Decay | Late Decay | Floor |
|-----|----|----|-----|-----|-------------|------------|-------|
| whale | 85% | 70% | 55% | 40% | 0.03 | 0.008 | 0.35 |
| dolphin | 70% | 45% | 25% | 12% | 0.07 | 0.015 | 0.08 |
| minnow | 55% | 30% | 12% | 5% | 0.09 | 0.020 | 0.03 |
| free_engaged | 50% | 25% | 10% | 4% | 0.10 | 0.022 | 0.02 |
| free_casual | 40% | 15% | 5% | 2% | 0.14 | 0.025 | 0.01 |
| free_churner | 25% | 5% | 1% | 0.2% | 0.25 | 0.030 | 0.001 |

### 3.3. Churn Decision

Каждый день симулятор проверяет, вернётся ли агент:

```python
def will_return_today(agent, day: int, rng: Random) -> bool:
    """Решение о возврате в игру."""
    base_prob = base_retention_probability(day, agent.type)
    
    # Модификаторы
    modifiers = 1.0
    
    # A/B тесты
    modifiers *= get_ab_retention_modifier(agent, day)
    
    # Негативный опыт (проигрыши, нехватка ресурсов)
    if agent.state.consecutive_losses > 3:
        modifiers *= 0.85
    
    # Позитивный опыт (новый герой, прогресс)
    if agent.state.got_legendary_recently:
        modifiers *= 1.15
    
    # Социальные связи
    if agent.state.in_active_guild:
        modifiers *= 1.10
    
    final_prob = min(base_prob * modifiers, 0.99)
    return rng.random() < final_prob
```

---

## 4. Session Model

### 4.1. Количество сессий в день

```python
def get_sessions_today(agent, day: int, rng: Random) -> int:
    """Сколько сессий будет сегодня."""
    if not will_return_today(agent, day, rng):
        return 0
    
    min_sessions, max_sessions = AGENT_PARAMS[agent.type]["sessions_per_day"]
    
    # Базовое количество (треугольное распределение, пик ближе к min)
    base = rng.triangular(min_sessions, max_sessions, min_sessions * 1.2)
    
    # Модификаторы
    # День недели (выходные +20%)
    if is_weekend(day):
        base *= 1.2
    
    # A/B тест energy_regen_rate
    if agent.ab_tests.get("energy_regen_rate") == "fast":
        base *= 1.2
    elif agent.ab_tests.get("energy_regen_rate") == "slow":
        base *= 0.85
    
    return max(1, round(base))
```

### 4.2. Время сессий (часы)

Распределение времени входа в игру:

| Период | Доля сессий | Описание |
|--------|-------------|----------|
| 00:00–07:00 | 5% | Ночь |
| 07:00–09:00 | 15% | Утро, перед работой |
| 09:00–12:00 | 10% | Рабочее утро |
| 12:00–14:00 | 20% | Обед |
| 14:00–18:00 | 10% | Рабочий день |
| 18:00–21:00 | 25% | Вечер (пик) |
| 21:00–00:00 | 15% | Поздний вечер |

```python
SESSION_TIME_WEIGHTS = [
    (0, 7, 0.05),
    (7, 9, 0.15),
    (9, 12, 0.10),
    (12, 14, 0.20),
    (14, 18, 0.10),
    (18, 21, 0.25),
    (21, 24, 0.15),
]
```

### 4.3. Длительность сессии

```python
def get_session_duration_minutes(agent, session_number: int, rng: Random) -> int:
    """Длительность сессии в минутах."""
    min_dur, max_dur = AGENT_PARAMS[agent.type]["session_duration_min"]
    
    # Первая сессия дня обычно длиннее (idle rewards, daily quests)
    if session_number == 1:
        base = rng.triangular(min_dur, max_dur, max_dur * 0.7)
    else:
        base = rng.triangular(min_dur, max_dur * 0.7, min_dur * 1.3)
    
    return max(2, round(base))
```

---

## 5. In-Session Behavior

### 5.1. Action Priority Queue

Каждую сессию агент выполняет действия в порядке приоритета:

```python
SESSION_ACTION_PRIORITIES = [
    ("claim_idle_rewards", 0.99),      # Почти всегда первым делом
    ("claim_daily_login", 0.95),       # Если не получал сегодня
    ("check_daily_quests", 0.90),      # Посмотреть задания
    ("spend_energy_campaign", 0.85),   # Основной геймплей
    ("upgrade_heroes", 0.70),          # Если есть ресурсы
    ("do_gacha", 0.50),                # Если есть тикеты/гемы
    ("arena_battles", 0.60),           # Если открыта и есть попытки
    ("guild_boss", 0.55),              # Если в гильдии и не атаковал
    ("watch_ads", 0.40),               # Зависит от типа агента
    ("browse_shop", 0.30),             # Зависит от типа агента
    ("claim_quest_rewards", 0.80),     # В конце сессии
]
```

### 5.2. Campaign Progression

```python
def decide_stage_attempt(agent, rng: Random) -> bool:
    """Решение попробовать пройти уровень."""
    if agent.state.energy < 6:
        return False
    
    current_stage = agent.state.max_stage
    stage_power_req = get_stage_power_requirement(current_stage + 1)
    team_power = agent.state.team_power
    
    # Отношение силы к требованию
    power_ratio = team_power / stage_power_req
    
    if power_ratio >= 1.2:
        # Сильно превосходим — точно пойдём
        return True
    elif power_ratio >= 1.0:
        # Примерно равны — 80% шанс
        return rng.random() < 0.80
    elif power_ratio >= 0.8:
        # Немного слабее — 40% шанс (рискуем)
        return rng.random() < 0.40
    else:
        # Слишком слабые — 10% шанс (упёртые игроки)
        return rng.random() < 0.10

def simulate_stage_result(agent, stage_id: str, rng: Random) -> dict:
    """Симуляция результата прохождения уровня."""
    stage_power_req = get_stage_power_requirement(stage_id)
    team_power = agent.state.team_power
    power_ratio = team_power / stage_power_req
    
    # Вероятность успеха
    if power_ratio >= 1.3:
        success_prob = 0.98
    elif power_ratio >= 1.1:
        success_prob = 0.85
    elif power_ratio >= 1.0:
        success_prob = 0.70
    elif power_ratio >= 0.9:
        success_prob = 0.45
    elif power_ratio >= 0.8:
        success_prob = 0.25
    else:
        success_prob = 0.10
    
    success = rng.random() < success_prob
    
    if success:
        # Звёзды зависят от превосходства
        if power_ratio >= 1.3:
            stars = 3
        elif power_ratio >= 1.1:
            stars = 3 if rng.random() < 0.7 else 2
        else:
            stars = rng.choices([1, 2, 3], weights=[0.3, 0.5, 0.2])[0]
        
        return {"success": True, "stars": stars}
    else:
        return {"success": False, "stars": 0}
```

### 5.3. Gacha Behavior

```python
def decide_gacha_pull(agent, rng: Random) -> dict:
    """Решение о призыве."""
    gems = agent.state.gems
    tickets = agent.state.summon_tickets
    pity = agent.state.pity_counter
    
    # Приоритет: тикеты > гемы
    can_single_ticket = tickets >= 1
    can_single_gems = gems >= 300
    can_multi_ticket = tickets >= 10
    can_multi_gems = gems >= 2700
    
    if not (can_single_ticket or can_single_gems):
        return {"action": "none"}
    
    # Факторы решения
    pull_desire = 0.0
    
    # Базовое желание по типу агента
    pull_desire += AGENT_PARAMS[agent.type]["gacha_desire_base"]
    
    # Pity близко — сильнее хотим тянуть
    if pity >= 75:
        pull_desire += 0.4
    elif pity >= 50:
        pull_desire += 0.2
    
    # A/B тест: видимость pity
    if agent.ab_tests.get("gacha_pity_display") == "visible" and pity >= 50:
        pull_desire += 0.15
    
    # Limited баннер с желанным героем
    if has_desired_limited_banner(agent):
        pull_desire += 0.25
    
    # Решение
    if rng.random() < pull_desire:
        # Multi или single?
        if can_multi_ticket:
            return {"action": "multi", "currency": "tickets"}
        elif can_multi_gems and agent.type in ["whale", "dolphin"]:
            return {"action": "multi", "currency": "gems"}
        elif can_single_ticket:
            return {"action": "single", "currency": "tickets"}
        else:
            return {"action": "single", "currency": "gems"}
    
    return {"action": "none"}
```

### 5.4. Hero Upgrade Behavior

```python
def decide_hero_upgrade(agent, rng: Random) -> dict:
    """Решение о прокачке героя."""
    gold = agent.state.gold
    team = agent.state.team_heroes
    
    # Находим героя с лучшим ROI для прокачки
    best_upgrade = None
    best_score = 0
    
    for hero in team:
        cost = get_levelup_cost(hero.level)
        if cost > gold:
            continue
        
        power_gain = get_levelup_power_gain(hero)
        score = power_gain / cost  # ROI
        
        # Предпочитаем качать main team
        if hero in agent.state.main_team:
            score *= 1.5
        
        # Предпочитаем качать редких
        rarity_mult = {"common": 0.5, "rare": 0.8, "epic": 1.2, "legendary": 1.5}
        score *= rarity_mult[hero.rarity]
        
        if score > best_score:
            best_score = score
            best_upgrade = hero
    
    if best_upgrade and rng.random() < 0.7:  # 70% решимся качать
        return {"action": "levelup", "hero": best_upgrade}
    
    return {"action": "none"}
```

---

## 6. Monetization Behavior

### 6.1. IAP Decision Model

```python
def decide_iap_purchase(agent, trigger: str, rng: Random) -> dict:
    """Решение о покупке IAP."""
    
    if agent.type in ["free_engaged", "free_casual", "free_churner"]:
        # F2P игроки крайне редко конвертируются
        if rng.random() > 0.001:  # 0.1% шанс конверсии
            return {"action": "none"}
    
    # Триггеры покупки
    triggers = {
        "starter_pack_offer": 0.15,      # Показали стартер пак
        "out_of_gems_gacha": 0.08,       # Хотел крутить, не хватило
        "out_of_energy": 0.03,           # Закончилась энергия
        "pity_close": 0.12,              # Pity близко, хочется дотянуть
        "limited_banner_ending": 0.10,   # Баннер заканчивается
        "stuck_progression": 0.05,       # Застрял на уровне
        "monthly_pass_reminder": 0.20,   # Напоминание о месячном пассе
    }
    
    base_probability = triggers.get(trigger, 0.02)
    
    # Модификаторы по типу агента
    type_multipliers = {
        "whale": 3.0,
        "dolphin": 1.5,
        "minnow": 0.8,
        "free_engaged": 0.1,
        "free_casual": 0.05,
        "free_churner": 0.02,
    }
    
    probability = base_probability * type_multipliers[agent.type]
    
    # A/B тест: цена стартер пака
    if trigger == "starter_pack_offer":
        if agent.ab_tests.get("starter_pack_price") == "lower":
            probability *= 1.6
        elif agent.ab_tests.get("starter_pack_price") == "higher":
            probability *= 0.6
    
    # A/B тест: late game offer
    if trigger == "late_game_offer" and agent.state.days_since_install >= 30:
        variant = agent.ab_tests.get("late_game_offer")
        if variant == "discount_50":
            probability *= 1.25
        elif variant == "bonus_hero":
            probability *= 1.15
    
    # Решение
    if rng.random() < probability:
        product = select_product_for_trigger(agent, trigger)
        return {"action": "purchase", "product": product}
    
    return {"action": "none"}
```

### 6.2. Product Selection

```python
def select_product_for_trigger(agent, trigger: str) -> str:
    """Выбор продукта для покупки."""
    
    if trigger == "starter_pack_offer" and not agent.state.bought_starter_pack:
        return "starter_pack"
    
    if trigger == "monthly_pass_reminder" and not agent.state.has_active_monthly:
        return "monthly_pass"
    
    # Выбор gem pack по типу агента
    if agent.type == "whale":
        return rng.choice(["gems_tier4", "gems_tier5"])
    elif agent.type == "dolphin":
        return rng.choice(["gems_tier2", "gems_tier3", "gems_tier4"])
    else:  # minnow
        return rng.choice(["gems_tier1", "gems_tier2"])
```

### 6.3. Ad Watch Behavior

```python
def decide_watch_ad(agent, rng: Random) -> bool:
    """Решение о просмотре рекламы."""
    
    if agent.state.ads_watched_today >= agent.state.max_ads_per_day:
        return False
    
    base_prob = AGENT_PARAMS[agent.type]["ad_watch_probability"]
    
    # A/B тест: награда за рекламу
    if agent.ab_tests.get("ad_reward_amount") == "generous":
        base_prob *= 1.4
    elif agent.ab_tests.get("ad_reward_amount") == "stingy":
        base_prob *= 0.7
    
    # Меньше желания если много гемов
    if agent.state.gems > 1000:
        base_prob *= 0.7
    
    return rng.random() < base_prob
```

---

## 7. Social Behavior

### 7.1. Guild Participation

```python
def decide_guild_action(agent, rng: Random) -> dict:
    """Решение о действиях в гильдии."""
    
    if agent.state.player_level < 15:
        return {"action": "none"}  # Не открыто
    
    engagement = AGENT_PARAMS[agent.type]["guild_engagement"]
    
    # Вступление в гильдию
    if not agent.state.guild_id:
        if rng.random() < engagement * 0.3:  # 30% от engagement за день
            return {"action": "join_guild"}
        return {"action": "none"}
    
    # Атака гильд-босса
    if not agent.state.attacked_guild_boss_today:
        if rng.random() < engagement:
            return {"action": "attack_boss"}
    
    # Выход из гильдии (редко)
    if rng.random() < 0.005:  # 0.5% в день
        return {"action": "leave_guild"}
    
    return {"action": "none"}
```

### 7.2. Arena Participation

```python
def decide_arena_action(agent, rng: Random) -> dict:
    """Решение о действиях на арене."""
    
    if agent.state.player_level < 10:
        return {"action": "none"}  # Не открыто
    
    engagement = AGENT_PARAMS[agent.type]["arena_engagement"]
    attempts_left = agent.state.arena_attempts_today
    
    if attempts_left <= 0:
        # Купить попытку за гемы?
        if agent.type in ["whale", "dolphin"] and rng.random() < 0.2:
            return {"action": "buy_attempt"}
        return {"action": "none"}
    
    if rng.random() < engagement:
        return {"action": "battle"}
    
    return {"action": "none"}
```

---

## 8. Tutorial Behavior

### 8.1. Tutorial Flow

```python
TUTORIAL_STEPS = [
    {"id": "welcome", "name": "Welcome", "duration_range": (5, 15)},
    {"id": "first_hero", "name": "Get First Hero", "duration_range": (10, 30)},
    {"id": "first_battle", "name": "First Battle", "duration_range": (20, 60)},
    {"id": "upgrade_hero", "name": "Upgrade Hero", "duration_range": (15, 40)},
    {"id": "second_battle", "name": "Second Battle", "duration_range": (15, 45)},
    {"id": "gacha_intro", "name": "Gacha Introduction", "duration_range": (20, 50)},
    {"id": "team_building", "name": "Team Building", "duration_range": (15, 35)},
    {"id": "daily_quests", "name": "Daily Quests Intro", "duration_range": (10, 25)},
]

def simulate_tutorial(agent, rng: Random) -> list:
    """Симуляция прохождения туториала."""
    events = []
    
    # A/B тест: длина туториала
    variant = agent.ab_tests.get("onboarding_length", "control")
    
    if variant == "short":
        steps = TUTORIAL_STEPS[:4]  # Только первые 4 шага
    elif variant == "extended":
        steps = TUTORIAL_STEPS + [
            {"id": "arena_preview", "name": "Arena Preview", "duration_range": (20, 40)},
            {"id": "shop_tour", "name": "Shop Tour", "duration_range": (15, 30)},
            {"id": "guild_preview", "name": "Guild Preview", "duration_range": (15, 35)},
            {"id": "advanced_tips", "name": "Advanced Tips", "duration_range": (10, 25)},
        ]
    else:
        steps = TUTORIAL_STEPS
    
    for i, step in enumerate(steps):
        # Шанс пропустить шаг (после первых двух обязательных)
        skipped = False
        if i >= 2 and rng.random() < 0.1:  # 10% пропускают
            skipped = True
            duration = rng.randint(1, 3)
        else:
            duration = rng.randint(*step["duration_range"])
        
        events.append({
            "event": "tutorial_step",
            "step_id": step["id"],
            "step_number": i + 1,
            "step_name": step["name"],
            "duration_sec": duration,
            "is_skipped": skipped,
        })
    
    return events
```

---

## 9. A/B Test Effects Summary

| Тест | Параметр | Control | Variant Effect |
|------|----------|---------|----------------|
| `onboarding_length` | Tutorial steps | 8 | short: 4, extended: 12 |
| `onboarding_length` | D1 retention | base | short: +5%, extended: -3% |
| `onboarding_length` | D7 retention | base | short: -8%, extended: +4% |
| `starter_pack_price` | Price | $0.99 | higher: $1.99, lower: $0.49 |
| `starter_pack_price` | Conversion | base | higher: -40%, lower: +60% |
| `gacha_pity_display` | Pity visible | no | visible: yes |
| `gacha_pity_display` | Pulls when pity>50 | base | visible: +15% |
| `energy_regen_rate` | Regen time | 5 min | fast: 4 min, slow: 6 min |
| `energy_regen_rate` | Sessions/day | base | fast: +20%, slow: -15% |
| `energy_regen_rate` | Energy purchases | base | fast: -30%, slow: +25% |
| `ad_reward_amount` | Reward | 50 gems | generous: 100, stingy: 25 |
| `ad_reward_amount` | Ad views | base | generous: +40%, stingy: -30% |
| `ad_reward_amount` | IAP conversion | base | generous: -10%, stingy: +5% |
| `late_game_offer` | Activation | N/A | day >= 30 |
| `late_game_offer` | IAP conversion (d30+) | base | discount: +25%, bonus: +15% |
| `late_game_offer` | D30-D60 retention | base | bonus: +10% |

---

## 10. Agent State Structure

```python
@dataclass
class AgentState:
    # Identity
    user_id: str
    device_id: str
    agent_type: str  # whale, dolphin, etc.
    
    # Install info
    install_date: datetime
    install_source: str
    country: str
    platform: str
    
    # A/B tests
    ab_tests: dict[str, str]
    
    # Progression
    player_level: int = 1
    player_exp: int = 0
    current_chapter: int = 1
    current_stage: int = 1
    max_chapter: int = 1
    max_stage: int = 1
    tutorial_completed: bool = False
    
    # Economy
    gold: int = 0
    gems: int = 0
    summon_tickets: int = 0
    energy: int = 120
    energy_last_update: datetime = None
    
    # Monetization
    total_spent_usd: float = 0.0
    vip_level: int = 0
    purchase_count: int = 0
    bought_starter_pack: bool = False
    has_active_monthly: bool = False
    monthly_pass_day: int = 0
    
    # Heroes
    heroes: dict[str, HeroInstance] = field(default_factory=dict)
    team: list[str] = field(default_factory=list)  # hero_ids
    team_power: int = 0
    
    # Gacha
    pity_counter: int = 0
    total_gacha_pulls: int = 0
    
    # Social
    guild_id: str = None
    guild_joined_date: datetime = None
    arena_rank: int = 0
    arena_rating: int = 1000
    
    # Daily state (resets each day)
    sessions_today: int = 0
    ads_watched_today: int = 0
    arena_attempts_today: int = 5
    attacked_guild_boss_today: bool = False
    claimed_daily_login: bool = False
    daily_quests_progress: dict = field(default_factory=dict)
    
    # Engagement tracking
    total_sessions: int = 0
    total_playtime_sec: int = 0
    last_session_date: datetime = None
    login_streak: int = 0
    consecutive_losses: int = 0
    got_legendary_recently: bool = False
    
    # Churn
    is_churned: bool = False
    churn_date: datetime = None
```

---

## 11. Simulation Flow

```python
def simulate_day(agent: Agent, day: int, sim_date: datetime, rng: Random) -> list[Event]:
    """Симуляция одного дня для агента."""
    events = []
    
    # 1. Проверка churn
    if agent.state.is_churned:
        return []
    
    if not will_return_today(agent, day, rng):
        # Проверяем окончательный churn
        if rng.random() < get_permanent_churn_probability(agent, day):
            agent.state.is_churned = True
            agent.state.churn_date = sim_date
        return []
    
    # 2. Reset daily state
    reset_daily_state(agent, sim_date)
    
    # 3. Energy regeneration
    regenerate_energy(agent, sim_date)
    
    # 4. Determine sessions
    num_sessions = get_sessions_today(agent, day, rng)
    session_times = generate_session_times(num_sessions, sim_date, rng)
    
    # 5. Simulate each session
    for session_idx, session_start in enumerate(session_times):
        session_events = simulate_session(
            agent, 
            session_idx + 1,
            session_start,
            day,
            rng
        )
        events.extend(session_events)
    
    # 6. Daily snapshot (if had at least one session)
    if num_sessions > 0 and is_first_session_of_day(agent, sim_date):
        events.append(create_player_snapshot(agent, sim_date))
    
    return events
```

---

## 12. Cohort Effects (Traffic Quality)

Разные источники трафика дают разное качество игроков.

### 12.1. Install Sources

| Source | Доля | Retention Modifier | Monetization Modifier | Описание |
|--------|------|-------------------|----------------------|----------|
| `organic` | 40% | 1.0 | 1.0 | Органический трафик |
| `google_ads` | 25% | 0.9 | 1.1 | Google Ads кампании |
| `facebook` | 20% | 0.85 | 1.05 | Facebook/Meta Ads |
| `unity_ads` | 10% | 0.75 | 0.8 | Unity Ads network |
| `influencer` | 5% | 1.1 | 0.9 | От блогеров |

### 12.2. Bad Traffic Event

Для учебных целей симулируем "закупку плохого трафика" в определённый день:

```python
BAD_TRAFFIC_CONFIG = {
    "enabled": True,
    "date": "day_25",              # На 25-й день симуляции
    "source": "fake_network",       # Название источника
    "volume": 2000,                 # Сколько установок
    "retention_modifier": 0.3,      # Очень плохой retention
    "monetization_modifier": 0.1,   # Почти не платят
    "bot_ratio": 0.4,               # 40% — боты (1-2 сессии и churn)
}
```

**Что студенты увидят:**
- Резкий spike установок на day 25
- Аномально низкий D1 retention для этой когорты
- Почти нулевая монетизация
- Подозрительные паттерны (короткие сессии, нет прогрессии)

**Задания:**
- Обнаружить аномальную когорту
- Оценить качество трафика по источникам
- Рассчитать "честные" метрики без плохого трафика

---

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 0.1 | 2025-02-01 | Первый драфт. 6 типов агентов, retention/session/monetization модели, A/B эффекты, bad traffic event. Утверждён. |
