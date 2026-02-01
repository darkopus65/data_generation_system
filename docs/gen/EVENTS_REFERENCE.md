# Справочник событий

Полный справочник по всем 36 типам событий, генерируемых симулятором.

## Содержание

- [Общая структура события](#общая-структура-события)
- [Session Events (2)](#session-events)
- [Economy Events (2)](#economy-events)
- [Progression Events (5)](#progression-events)
- [Gacha Events (2)](#gacha-events)
- [Hero Events (3)](#hero-events)
- [Shop Events (4)](#shop-events)
- [Ads Events (4)](#ads-events)
- [Social Events (5)](#social-events)
- [Quest Events (2)](#quest-events)
- [Event Events (3)](#event-events)
- [System Events (4)](#system-events)
- [Сводная таблица](#сводная-таблица)

---

## Общая структура события

Каждое событие содержит общие поля и специфичные для типа события свойства:

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440000",
  "event_name": "stage_complete",
  "event_timestamp": "2025-01-15T14:32:05.123Z",

  "user_id": "u_000001",
  "session_id": "s_abc123",

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
    // специфичные для события поля
  }
}
```

### Общие поля

| Поле | Тип | Описание |
|------|-----|----------|
| `event_id` | string (UUID) | Уникальный идентификатор события |
| `event_name` | string | Название события (snake_case) |
| `event_timestamp` | string (ISO 8601) | Время события в UTC |
| `user_id` | string | Уникальный ID игрока |
| `session_id` | string | ID текущей сессии |

### Блок device

| Поле | Тип | Описание |
|------|-----|----------|
| `device_id` | string | Уникальный ID устройства |
| `platform` | string | `ios` или `android` |
| `os_version` | string | Версия ОС |
| `app_version` | string | Версия приложения (semver) |
| `device_model` | string | Модель устройства |
| `country` | string | Страна (ISO 3166-1 alpha-2) |
| `language` | string | Язык (ISO 639-1) |

### Блок user_properties

| Поле | Тип | Описание |
|------|-----|----------|
| `player_level` | int | Текущий уровень игрока |
| `vip_level` | int | VIP уровень (0-10) |
| `total_spent_usd` | float | Сумма всех покупок в USD |
| `days_since_install` | int | Дней с момента установки |
| `cohort_date` | string | Дата установки (YYYY-MM-DD) |
| `current_chapter` | int | Текущая глава кампании |

### Блок ab_tests

Словарь активных A/B тестов. Ключ — название теста, значение — вариант.

---

## Session Events

События жизненного цикла сессий.

### session_start

Начало игровой сессии.

| Поле | Тип | Описание |
|------|-----|----------|
| `session_number` | int | Порядковый номер сессии игрока |
| `is_first_session` | bool | Первая сессия (install) |
| `time_since_last_session_sec` | int/null | Секунд с прошлой сессии |
| `install_source` | string | Источник установки |

**Возможные install_source:**
- `organic` — органическая установка
- `google_ads` — Google Ads
- `facebook` — Meta Ads
- `unity_ads` — Unity Ads
- `influencer` — influencer marketing
- `fake_network` — некачественный трафик (сценарий)

### session_end

Конец игровой сессии.

| Поле | Тип | Описание |
|------|-----|----------|
| `session_duration_sec` | int | Длительность сессии в секундах |
| `events_count` | int | Количество событий за сессию |
| `stages_played` | int | Уровней пройдено за сессию |
| `gems_spent` | int | Гемов потрачено за сессию |
| `gold_spent` | int | Золота потрачено за сессию |

---

## Economy Events

События экономики — получение и трата валют.

### economy_source

Получение валюты.

| Поле | Тип | Описание |
|------|-----|----------|
| `currency` | string | Тип валюты |
| `amount` | int | Количество |
| `balance_after` | int | Баланс после получения |
| `source` | string | Источник |
| `source_id` | string | ID источника (опционально) |

**Возможные currency:**
- `gold` — мягкая валюта
- `gems` — твёрдая валюта
- `summon_tickets` — тикеты призыва
- `energy` — энергия

**Возможные source:**

| Source | Описание |
|--------|----------|
| `stage_reward` | Награда за уровень |
| `idle_reward` | Idle накопление |
| `quest_reward` | Награда за квест |
| `arena_reward` | Награда за арену |
| `guild_reward` | Награда гильдии |
| `iap_purchase` | Покупка IAP |
| `ad_reward` | Просмотр рекламы |
| `login_reward` | Ежедневный вход |
| `achievement` | Достижение |
| `event_reward` | Временное событие |
| `energy_regen` | Регенерация энергии |
| `vip_bonus` | VIP бонус |

### economy_sink

Трата валюты.

| Поле | Тип | Описание |
|------|-----|----------|
| `currency` | string | Тип валюты |
| `amount` | int | Количество |
| `balance_after` | int | Баланс после траты |
| `sink` | string | Куда потрачено |
| `sink_id` | string | ID (опционально) |

**Возможные sink:**

| Sink | Описание |
|------|----------|
| `hero_levelup` | Прокачка героя |
| `hero_ascend` | Повышение звёзд |
| `gacha_summon` | Призыв |
| `stage_entry` | Вход в уровень (energy) |
| `arena_attempt` | Попытка арены |
| `energy_refill` | Покупка энергии |
| `shop_purchase` | Покупка в магазине |

---

## Progression Events

События прогрессии в игре.

### stage_start

Начало уровня.

| Поле | Тип | Описание |
|------|-----|----------|
| `chapter` | int | Номер главы (1-20) |
| `stage` | int | Номер уровня в главе (1-10) |
| `stage_id` | string | Уникальный ID (например `ch03_st07`) |
| `attempt_number` | int | Попытка прохождения |
| `team_power` | int | Суммарная сила отряда |
| `team_size` | int | Количество героев в отряде |
| `hero_ids` | array[string] | ID героев в отряде |

### stage_complete

Успешное прохождение уровня.

| Поле | Тип | Описание |
|------|-----|----------|
| `chapter` | int | Номер главы |
| `stage` | int | Номер уровня |
| `stage_id` | string | Уникальный ID |
| `duration_sec` | int | Время прохождения |
| `stars` | int | Полученные звёзды (1-3) |
| `is_first_clear` | bool | Первое прохождение |
| `gold_reward` | int | Награда золотом |
| `exp_reward` | int | Награда опытом |
| `loot_items` | array[object] | Выпавший лут |

**Формат loot_items:**
```json
[
  {"item_id": "sword_01", "item_type": "equipment"},
  {"item_id": "potion_hp", "item_type": "consumable"}
]
```

### stage_fail

Провал уровня.

| Поле | Тип | Описание |
|------|-----|----------|
| `chapter` | int | Номер главы |
| `stage` | int | Номер уровня |
| `stage_id` | string | Уникальный ID |
| `duration_sec` | int | Время до провала |
| `fail_reason` | string | Причина провала |
| `team_power` | int | Сила отряда |
| `required_power` | int | Рекомендуемая сила |

**Возможные fail_reason:**
- `defeat` — поражение в бою
- `timeout` — время вышло
- `abandon` — игрок вышел

### idle_reward_claim

Сбор idle наград.

| Поле | Тип | Описание |
|------|-----|----------|
| `idle_duration_sec` | int | Накопленное время (max 43200 = 12h) |
| `gold_earned` | int | Золото |
| `exp_earned` | int | Опыт |
| `max_stage_id` | string | Максимальный пройденный уровень |

### player_levelup

Повышение уровня игрока.

| Поле | Тип | Описание |
|------|-----|----------|
| `old_level` | int | Был уровень |
| `new_level` | int | Стал уровень |
| `unlocked_features` | array[string] | Что открылось |

**Возможные unlocked_features:**
- `gacha` — призыв героев (Lv.3)
- `daily_quests` — ежедневные квесты (Lv.5)
- `events` — события (Lv.5)
- `arena` — арена (Lv.10)
- `guild` — гильдии (Lv.15)

---

## Gacha Events

События призыва героев.

### gacha_banner_view

Просмотр баннера (открыл экран гачи).

| Поле | Тип | Описание |
|------|-----|----------|
| `banner_id` | string | ID баннера |
| `banner_type` | string | `standard`, `limited` |
| `featured_hero_id` | string/null | Featured герой |
| `player_gems` | int | Гемов у игрока |
| `player_tickets` | int | Тикетов у игрока |
| `can_afford_single` | bool | Хватает на 1 призыв |
| `can_afford_multi` | bool | Хватает на 10 призывов |

### gacha_summon

Призыв героя. Одно событие на каждого призванного героя.

| Поле | Тип | Описание |
|------|-----|----------|
| `banner_id` | string | ID баннера |
| `banner_type` | string | `standard`, `limited` |
| `summon_type` | string | `single`, `multi_10` |
| `summon_index` | int | Индекс в мульти-призыве (1-10) |
| `summon_cost_currency` | string | `gems`, `summon_tickets` |
| `summon_cost_amount` | int | Потрачено (для первого в мульти) |
| `hero_id` | string | Полученный герой |
| `hero_name` | string | Имя героя |
| `hero_rarity` | string | `common`, `rare`, `epic`, `legendary` |
| `hero_class` | string | `warrior`, `mage`, `archer`, `healer`, `tank` |
| `is_new` | bool | Новый герой |
| `is_duplicate` | bool | Уже был этот герой |
| `is_featured` | bool | Featured герой баннера |
| `pity_counter_before` | int | Счётчик pity до призыва |
| `pity_counter_after` | int | Счётчик pity после |
| `pity_triggered` | bool | Сработала ли гарантия |

---

## Hero Events

События действий с героями.

### hero_levelup

Повышение уровня героя.

| Поле | Тип | Описание |
|------|-----|----------|
| `hero_id` | string | ID героя |
| `hero_name` | string | Имя героя |
| `hero_rarity` | string | Редкость |
| `old_level` | int | Был уровень |
| `new_level` | int | Стал уровень |
| `gold_spent` | int | Потрачено золота |
| `power_before` | int | Сила до |
| `power_after` | int | Сила после |

### hero_ascend

Повышение звёзд героя.

| Поле | Тип | Описание |
|------|-----|----------|
| `hero_id` | string | ID героя |
| `hero_name` | string | Имя героя |
| `hero_rarity` | string | Редкость |
| `old_stars` | int | Было звёзд |
| `new_stars` | int | Стало звёзд |
| `duplicates_used` | int | Потрачено дубликатов |
| `power_before` | int | Сила до |
| `power_after` | int | Сила после |

### hero_team_change

Изменение состава отряда.

| Поле | Тип | Описание |
|------|-----|----------|
| `old_team` | array[string] | Предыдущий состав (hero_ids) |
| `new_team` | array[string] | Новый состав |
| `team_power_before` | int | Сила до |
| `team_power_after` | int | Сила после |
| `change_reason` | string | Причина изменения |

**Возможные change_reason:**
- `manual` — ручная замена
- `new_hero` — добавлен новый герой
- `auto_optimize` — авто-подбор

---

## Shop Events

События магазина и IAP.

### shop_view

Открытие магазина.

| Поле | Тип | Описание |
|------|-----|----------|
| `shop_tab` | string | Какую вкладку открыл |
| `player_gems` | int | Текущий баланс гемов |

**Возможные shop_tab:**
- `iap` — покупки за реальные деньги
- `gems` — покупки за гемы
- `daily` — ежедневные предложения
- `special` — специальные офферы

### iap_initiated

Начало покупки (нажал "купить").

| Поле | Тип | Описание |
|------|-----|----------|
| `product_id` | string | ID продукта |
| `product_name` | string | Название |
| `price_usd` | float | Цена в USD |

### iap_purchase

Успешная покупка IAP.

| Поле | Тип | Описание |
|------|-----|----------|
| `product_id` | string | ID продукта |
| `product_name` | string | Название |
| `price_usd` | float | Цена в USD |
| `gems_received` | int | Получено гемов |
| `items_received` | array[object] | Другие предметы |
| `is_first_purchase` | bool | Первая покупка |
| `purchase_number` | int | Номер покупки игрока |
| `transaction_id` | string | ID транзакции |
| `vip_points_earned` | int | Получено VIP очков |

**Формат items_received:**
```json
[
  {"item_id": "summon_ticket", "amount": 10}
]
```

### iap_failed

Провал покупки.

| Поле | Тип | Описание |
|------|-----|----------|
| `product_id` | string | ID продукта |
| `price_usd` | float | Цена |
| `fail_reason` | string | Причина провала |

**Возможные fail_reason:**
- `cancelled` — отменено пользователем
- `payment_error` — ошибка оплаты
- `network_error` — сетевая ошибка
- `insufficient_funds` — недостаточно средств

---

## Ads Events

События рекламных просмотров.

### ad_opportunity

Появилась возможность посмотреть рекламу.

| Поле | Тип | Описание |
|------|-----|----------|
| `placement` | string | Размещение |
| `ads_watched_today` | int | Уже просмотрено сегодня |
| `ads_available` | int | Доступно ещё |

**Возможные placement:**
- `main_screen` — главный экран
- `shop` — магазин
- `stage_fail` — после провала уровня
- `energy_refill` — восполнение энергии

### ad_started

Начало просмотра рекламы.

| Поле | Тип | Описание |
|------|-----|----------|
| `placement` | string | Размещение |
| `ad_network` | string | Рекламная сеть |

**Возможные ad_network:**
- `unity_ads`
- `applovin`
- `ironsource`
- `admob`

### ad_completed

Успешный просмотр рекламы.

| Поле | Тип | Описание |
|------|-----|----------|
| `placement` | string | Размещение |
| `ad_network` | string | Рекламная сеть |
| `reward_currency` | string | Валюта награды |
| `reward_amount` | int | Количество |
| `watch_duration_sec` | int | Длительность просмотра |

### ad_skipped

Пропуск/закрытие рекламы без награды.

| Поле | Тип | Описание |
|------|-----|----------|
| `placement` | string | Размещение |
| `ad_network` | string | Рекламная сеть |
| `skip_after_sec` | int | Через сколько закрыл |
| `skip_reason` | string | Причина |

**Возможные skip_reason:**
- `user_closed` — закрыл вручную
- `ad_error` — ошибка загрузки
- `timeout` — таймаут

---

## Social Events

События арены и гильдий.

### arena_battle_start

Начало боя на арене.

| Поле | Тип | Описание |
|------|-----|----------|
| `opponent_user_id` | string | ID противника |
| `opponent_power` | int | Сила противника |
| `opponent_rank` | int | Ранг противника |
| `player_power` | int | Сила игрока |
| `player_rank` | int | Текущий ранг игрока |
| `attempt_number` | int | Номер попытки сегодня |
| `is_paid_attempt` | bool | Платная попытка |

### arena_battle_end

Конец боя на арене.

| Поле | Тип | Описание |
|------|-----|----------|
| `opponent_user_id` | string | ID противника |
| `result` | string | `win`, `lose` |
| `duration_sec` | int | Длительность |
| `rank_before` | int | Ранг до боя |
| `rank_after` | int | Ранг после боя |
| `rating_change` | int | Изменение рейтинга |
| `reward_currency` | string | Валюта награды (если win) |
| `reward_amount` | int | Количество награды |

### guild_join

Вступление в гильдию.

| Поле | Тип | Описание |
|------|-----|----------|
| `guild_id` | string | ID гильдии |
| `guild_name` | string | Название |
| `guild_member_count` | int | Участников в гильдии |
| `join_method` | string | Способ вступления |

**Возможные join_method:**
- `search` — нашёл в поиске
- `invite` — по приглашению
- `create` — создал новую

### guild_leave

Выход из гильдии.

| Поле | Тип | Описание |
|------|-----|----------|
| `guild_id` | string | ID гильдии |
| `guild_name` | string | Название |
| `reason` | string | Причина выхода |
| `days_in_guild` | int | Дней в гильдии |

**Возможные reason:**
- `voluntary` — добровольный выход
- `kicked` — исключён
- `guild_disbanded` — гильдия распущена

### guild_boss_attack

Атака гильд-босса.

| Поле | Тип | Описание |
|------|-----|----------|
| `guild_id` | string | ID гильдии |
| `boss_id` | string | ID босса |
| `boss_level` | int | Уровень босса |
| `damage_dealt` | int | Нанесённый урон |
| `team_power` | int | Сила отряда |
| `attempt_number` | int | Попытка сегодня |
| `boss_hp_remaining_pct` | float | Оставшееся HP босса (%) |

---

## Quest Events

События квестов и достижений.

### quest_complete

Выполнение квеста.

| Поле | Тип | Описание |
|------|-----|----------|
| `quest_id` | string | ID квеста |
| `quest_type` | string | Тип квеста |
| `quest_name` | string | Название |
| `reward_currency` | string | Валюта награды |
| `reward_amount` | int | Количество |
| `time_to_complete_sec` | int | Время на выполнение (опционально) |

**Возможные quest_type:**
- `daily` — ежедневный
- `weekly` — еженедельный
- `achievement` — достижение (разовый)

### daily_login

Ежедневный вход (отмечен в календаре).

| Поле | Тип | Описание |
|------|-----|----------|
| `login_streak` | int | Серия входов подряд |
| `reward_day` | int | День в месячном календаре (1-30) |
| `reward_currency` | string | Валюта награды |
| `reward_amount` | int | Количество |
| `is_streak_bonus` | bool | Бонус за серию |

---

## Event Events

События временных активностей (игровые события).

### event_start

Игрок начал участие в событии.

| Поле | Тип | Описание |
|------|-----|----------|
| `event_id` | string | ID события |
| `event_type` | string | Тип события |
| `event_name` | string | Название |
| `event_start_date` | string | Дата начала события |
| `event_end_date` | string | Дата окончания |
| `days_remaining` | int | Дней до конца |

**Возможные event_type:**
- `login_event` — бонусы за вход
- `summon_event` — бонусы за призывы
- `spending_event` — бонусы за траты
- `collection_event` — сбор предметов

### event_progress

Прогресс в событии.

| Поле | Тип | Описание |
|------|-----|----------|
| `event_id` | string | ID события |
| `event_type` | string | Тип события |
| `milestone_reached` | int | Достигнутая веха |
| `milestone_target` | int | Цель вехи |
| `progress_value` | int | Текущий прогресс |
| `reward_claimed` | bool | Забрана ли награда |
| `reward_currency` | string | Валюта награды (опционально) |
| `reward_amount` | int | Количество (опционально) |

### event_complete

Завершение события (игрок достиг финальной цели).

| Поле | Тип | Описание |
|------|-----|----------|
| `event_id` | string | ID события |
| `event_type` | string | Тип события |
| `total_progress` | int | Итоговый прогресс |
| `milestones_completed` | int | Вех завершено |
| `total_rewards_currency` | string | Основная валюта наград |
| `total_rewards_amount` | int | Всего получено |

---

## System Events

Технические и системные события.

### player_state_snapshot

Ежедневный снимок состояния игрока. Генерируется при первом входе за день.

| Поле | Тип | Описание |
|------|-----|----------|
| `snapshot_date` | string | Дата снапшота (YYYY-MM-DD) |
| `player_level` | int | Уровень игрока |
| `vip_level` | int | VIP уровень |
| `total_spent_usd` | float | Всего потрачено |
| `gold_balance` | int | Баланс золота |
| `gems_balance` | int | Баланс гемов |
| `energy_balance` | int | Баланс энергии |
| `summon_tickets_balance` | int | Баланс тикетов |
| `heroes_count` | int | Количество уникальных героев |
| `heroes_by_rarity` | object | Распределение по редкости |
| `max_hero_level` | int | Максимальный уровень героя |
| `max_hero_stars` | int | Максимальные звёзды героя |
| `team_power` | int | Сила основного отряда |
| `max_chapter` | int | Максимальная глава |
| `max_stage` | int | Максимальный уровень |
| `total_stages_cleared` | int | Всего пройдено уровней |
| `arena_rank` | int/null | Ранг на арене |
| `arena_rating` | int/null | Рейтинг арены |
| `guild_id` | string/null | ID гильдии |
| `total_sessions` | int | Всего сессий |
| `total_playtime_sec` | int | Общее время в игре |
| `total_gacha_pulls` | int | Всего призывов |
| `pity_counter` | int | Текущий счётчик pity |
| `last_active_date` | string | Последняя активность |

**Формат heroes_by_rarity:**
```json
{
  "common": 15,
  "rare": 8,
  "epic": 3,
  "legendary": 1
}
```

### tutorial_step

Прохождение шага туториала.

| Поле | Тип | Описание |
|------|-----|----------|
| `step_id` | string | ID шага |
| `step_number` | int | Номер шага (1-8) |
| `step_name` | string | Название |
| `duration_sec` | int | Время на шаг |
| `is_skipped` | bool | Пропущен |

**Шаги туториала:**

| step_id | step_number | step_name |
|---------|-------------|-----------|
| `tut_welcome` | 1 | Welcome |
| `tut_first_battle` | 2 | First Battle |
| `tut_hero_summon` | 3 | Hero Summon |
| `tut_hero_levelup` | 4 | Hero Level Up |
| `tut_team_setup` | 5 | Team Setup |
| `tut_campaign` | 6 | Campaign Intro |
| `tut_idle_rewards` | 7 | Idle Rewards |
| `tut_complete` | 8 | Tutorial Complete |

### tutorial_complete

Завершение туториала.

| Поле | Тип | Описание |
|------|-----|----------|
| `total_duration_sec` | int | Общее время туториала |
| `steps_completed` | int | Пройдено шагов |
| `steps_skipped` | int | Пропущено шагов |

### error

Ошибка (для симуляции багов логирования).

| Поле | Тип | Описание |
|------|-----|----------|
| `error_type` | string | Тип ошибки |
| `error_code` | int | Код ошибки |
| `error_message` | string | Сообщение |
| `error_context` | string | Контекст (опционально) |

**Возможные error_type:**
- `network_error` — сетевая ошибка
- `validation_error` — ошибка валидации
- `state_error` — ошибка состояния
- `unknown_error` — неизвестная ошибка

---

## Сводная таблица

| # | Событие | Категория | Критичность | Частота |
|---|---------|-----------|-------------|---------|
| 1 | `session_start` | Session | Critical | Каждая сессия |
| 2 | `session_end` | Session | Critical | Каждая сессия |
| 3 | `economy_source` | Economy | High | Часто |
| 4 | `economy_sink` | Economy | High | Часто |
| 5 | `stage_start` | Progression | Medium | Часто |
| 6 | `stage_complete` | Progression | High | Часто |
| 7 | `stage_fail` | Progression | Medium | Средне |
| 8 | `idle_reward_claim` | Progression | Medium | 1-4/день |
| 9 | `player_levelup` | Progression | Medium | Редко |
| 10 | `gacha_banner_view` | Gacha | Low | Средне |
| 11 | `gacha_summon` | Gacha | High | Средне |
| 12 | `hero_levelup` | Hero | Medium | Часто |
| 13 | `hero_ascend` | Hero | Medium | Редко |
| 14 | `hero_team_change` | Hero | Low | Редко |
| 15 | `shop_view` | Shop | Low | Средне |
| 16 | `iap_initiated` | Shop | High | Редко |
| 17 | `iap_purchase` | Shop | Critical | Редко |
| 18 | `iap_failed` | Shop | High | Редко |
| 19 | `ad_opportunity` | Ads | Low | Часто |
| 20 | `ad_started` | Ads | Medium | Средне |
| 21 | `ad_completed` | Ads | Medium | Средне |
| 22 | `ad_skipped` | Ads | Low | Редко |
| 23 | `arena_battle_start` | Social | Medium | 1-5/день |
| 24 | `arena_battle_end` | Social | Medium | 1-5/день |
| 25 | `guild_join` | Social | Medium | Редко |
| 26 | `guild_leave` | Social | Medium | Редко |
| 27 | `guild_boss_attack` | Social | Medium | 1/день |
| 28 | `quest_complete` | Quest | Medium | 5-10/день |
| 29 | `daily_login` | Quest | Medium | 1/день |
| 30 | `event_start` | Event | Medium | Редко |
| 31 | `event_progress` | Event | Medium | Средне |
| 32 | `event_complete` | Event | Medium | Редко |
| 33 | `player_state_snapshot` | System | High | 1/день |
| 34 | `tutorial_step` | System | Medium | Только новые |
| 35 | `tutorial_complete` | System | Medium | 1 раз |
| 36 | `error` | System | Low | Симуляция |

**Итого: 36 событий**

---

## Примеры полных событий

### Пример: session_start

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

### Пример: gacha_summon

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440002",
  "event_name": "gacha_summon",
  "event_timestamp": "2025-01-15T14:05:32.456Z",
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
    "banner_id": "standard_banner",
    "banner_type": "standard",
    "summon_type": "multi_10",
    "summon_index": 3,
    "summon_cost_currency": "gems",
    "summon_cost_amount": 0,
    "hero_id": "hero_mage_003",
    "hero_name": "Frost Witch",
    "hero_rarity": "epic",
    "hero_class": "mage",
    "is_new": true,
    "is_duplicate": false,
    "is_featured": false,
    "pity_counter_before": 45,
    "pity_counter_after": 46,
    "pity_triggered": false
  }
}
```

### Пример: iap_purchase

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440003",
  "event_name": "iap_purchase",
  "event_timestamp": "2025-01-15T14:10:15.789Z",
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
    "product_id": "gems_tier2",
    "product_name": "Pile of Gems",
    "price_usd": 9.99,
    "gems_received": 1100,
    "items_received": [],
    "is_first_purchase": false,
    "purchase_number": 3,
    "transaction_id": "txn_1705329015789",
    "vip_points_earned": 999
  }
}
```

### Пример: player_state_snapshot

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440004",
  "event_name": "player_state_snapshot",
  "event_timestamp": "2025-01-15T08:00:00.000Z",
  "user_id": "u_000001",
  "session_id": "s_morning001",
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
    "snapshot_date": "2025-01-15",
    "player_level": 25,
    "vip_level": 2,
    "total_spent_usd": 14.99,
    "gold_balance": 125000,
    "gems_balance": 340,
    "energy_balance": 120,
    "summon_tickets_balance": 3,
    "heroes_count": 27,
    "heroes_by_rarity": {
      "common": 15,
      "rare": 8,
      "epic": 3,
      "legendary": 1
    },
    "max_hero_level": 45,
    "max_hero_stars": 4,
    "team_power": 12500,
    "max_chapter": 5,
    "max_stage": 7,
    "total_stages_cleared": 47,
    "arena_rank": 2547,
    "arena_rating": 1250,
    "guild_id": "guild_042",
    "total_sessions": 46,
    "total_playtime_sec": 86400,
    "total_gacha_pulls": 85,
    "pity_counter": 45,
    "last_active_date": "2025-01-15"
  }
}
```
