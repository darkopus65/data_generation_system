# Event Taxonomy v0.2
## "Idle Champions: Synthetic"

**Статус:** Утверждён  
**Дата:** 2025-02-01  
**Связан с:** GDD v0.2

---

## 1. Общая структура события

Каждое событие имеет единый формат:

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440000",
  "event_name": "stage_complete",
  "event_timestamp": "2025-01-15T14:32:05.123Z",
  
  "user_id": "u_abc123",
  "session_id": "s_xyz789",
  
  "device": {
    "device_id": "d_abc123",
    "platform": "ios",
    "os_version": "17.2",
    "app_version": "1.2.3",
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
    "onboarding_v2": "control",
    "new_gacha_rates": "variant_b"
  },
  
  "event_properties": {
    // специфичные для события поля
  }
}
```

### 1.1. Описание общих полей

| Поле | Тип | Описание |
|------|-----|----------|
| event_id | string (UUID) | Уникальный идентификатор события |
| event_name | string | Название события (snake_case) |
| event_timestamp | string (ISO 8601) | Время события в UTC |
| user_id | string | Уникальный ID игрока |
| session_id | string | ID текущей сессии |

### 1.2. Блок device

| Поле | Тип | Описание |
|------|-----|----------|
| device_id | string | Уникальный ID устройства |
| platform | string | ios, android |
| os_version | string | Версия ОС |
| app_version | string | Версия приложения (semver) |
| device_model | string | Модель устройства |
| country | string | Страна (ISO 3166-1 alpha-2) |
| language | string | Язык (ISO 639-1) |

### 1.3. Блок user_properties

Базовый набор, включается в каждое событие.

| Поле | Тип | Описание |
|------|-----|----------|
| player_level | int | Текущий уровень игрока |
| vip_level | int | VIP уровень (0-10) |
| total_spent_usd | float | Сумма всех покупок в USD |
| days_since_install | int | Дней с момента установки |
| cohort_date | string | Дата установки (YYYY-MM-DD) |
| current_chapter | int | Текущая глава кампании |

### 1.4. Блок ab_tests

Словарь активных A/B тестов для пользователя.

| Поле | Тип | Описание |
|------|-----|----------|
| {test_name} | string | Название варианта (control, variant_a, variant_b, etc.) |

Пустой объект `{}` если игрок не участвует ни в каких тестах.

---

## 2. Категории событий

| Категория | Префикс | Кол-во событий | Описание |
|-----------|---------|----------------|----------|
| Session | `session_` | 2 | Сессии и lifecycle |
| Economy | `economy_` | 2 | Получение и трата валют |
| Progression | `progression_` | 5 | Прохождение контента |
| Gacha | `gacha_` | 2 | Призывы героев |
| Hero | `hero_` | 3 | Действия с героями |
| Shop | `shop_` | 4 | Магазин и IAP |
| Ads | `ads_` | 4 | Рекламные просмотры |
| Social | `social_` | 5 | Arena, Guild |
| Quest | `quest_` | 2 | Квесты и достижения |
| Event | `event_` | 3 | Временные активности |
| System | `system_` | 4 | Технические события |

**Итого: 36 событий**

---

## 3. Session Events

### 3.1. session_start

Начало игровой сессии.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| session_number | int | да | Порядковый номер сессии игрока |
| is_first_session | bool | да | Первая сессия (install) |
| time_since_last_session_sec | int | нет | Секунд с прошлой сессии (null если первая) |
| install_source | string | да | Источник установки |

**Возможные install_source:**
- `organic` — органическая установка
- `facebook` — Facebook Ads
- `google` — Google Ads
- `unity_ads` — Unity Ads
- `influencer` — influencer marketing
- `cross_promo` — кросс-промо

### 3.2. session_end

Конец игровой сессии.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| session_duration_sec | int | да | Длительность сессии в секундах |
| events_count | int | да | Количество событий за сессию |
| stages_played | int | да | Уровней пройдено за сессию |
| gems_spent | int | да | Гемов потрачено за сессию |
| gold_spent | int | да | Золота потрачено за сессию |

---

## 4. Economy Events

### 4.1. economy_source

Получение валюты.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| currency | string | да | Тип валюты |
| amount | int | да | Количество |
| balance_after | int | да | Баланс после получения |
| source | string | да | Источник |
| source_id | string | нет | ID источника (stage_id, quest_id, etc.) |

**Возможные currency:**
- `gold` — мягкая валюта
- `gems` — твёрдая валюта
- `summon_tickets` — тикеты призыва
- `energy` — энергия

**Возможные source:**
| Source | Описание |
|--------|----------|
| stage_reward | Награда за уровень |
| idle_reward | Idle накопление |
| quest_reward | Награда за квест |
| arena_reward | Награда за арену |
| guild_reward | Награда гильдии |
| iap_purchase | Покупка IAP |
| ad_reward | Просмотр рекламы |
| login_reward | Ежедневный вход |
| achievement | Достижение |
| event_reward | Временное событие |
| compensation | Компенсация |
| energy_regen | Регенерация энергии |
| vip_bonus | VIP бонус |

### 4.2. economy_sink

Трата валюты.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| currency | string | да | Тип валюты |
| amount | int | да | Количество |
| balance_after | int | да | Баланс после траты |
| sink | string | да | Куда потрачено |
| sink_id | string | нет | ID (hero_id, stage_id, etc.) |

**Возможные sink:**
| Sink | Описание |
|------|----------|
| hero_levelup | Прокачка героя |
| hero_ascend | Повышение звёзд |
| gacha_summon | Призыв |
| stage_entry | Вход в уровень (energy) |
| arena_attempt | Попытка арены |
| energy_refill | Покупка энергии |
| shop_purchase | Покупка в магазине |

---

## 5. Progression Events

### 5.1. stage_start

Начало уровня.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| chapter | int | да | Номер главы (1-20) |
| stage | int | да | Номер уровня в главе (1-10) |
| stage_id | string | да | Уникальный ID (например "ch03_st07") |
| attempt_number | int | да | Попытка прохождения этого уровня |
| team_power | int | да | Суммарная сила отряда |
| team_size | int | да | Количество героев в отряде |
| hero_ids | array[string] | да | ID героев в отряде |

### 5.2. stage_complete

Успешное прохождение уровня.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| chapter | int | да | Номер главы |
| stage | int | да | Номер уровня |
| stage_id | string | да | Уникальный ID |
| duration_sec | int | да | Время прохождения |
| stars | int | да | Полученные звёзды (1-3) |
| is_first_clear | bool | да | Первое прохождение |
| gold_reward | int | да | Награда золотом |
| exp_reward | int | да | Награда опытом |
| loot_items | array[object] | да | Выпавший лут |

**Формат loot_items:**
```json
[
  {"item_id": "sword_01", "item_type": "equipment"},
  {"item_id": "potion_hp", "item_type": "consumable"}
]
```

### 5.3. stage_fail

Провал уровня.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| chapter | int | да | Номер главы |
| stage | int | да | Номер уровня |
| stage_id | string | да | Уникальный ID |
| duration_sec | int | да | Время до провала |
| fail_reason | string | да | Причина провала |
| team_power | int | да | Сила отряда |
| required_power | int | да | Рекомендуемая сила |

**Возможные fail_reason:**
- `defeat` — поражение в бою
- `timeout` — время вышло
- `abandon` — игрок вышел

### 5.4. idle_reward_claim

Сбор idle наград.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| idle_duration_sec | int | да | Накопленное время (max 43200 = 12h) |
| gold_earned | int | да | Золото |
| exp_earned | int | да | Опыт |
| max_stage_id | string | да | Максимальный пройденный уровень |

### 5.5. player_levelup

Повышение уровня игрока.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| old_level | int | да | Был уровень |
| new_level | int | да | Стал уровень |
| unlocked_features | array[string] | да | Что открылось |

**Возможные unlocked_features:**
- `gacha` — призыв героев (Lv.3)
- `daily_quests` — ежедневные квесты (Lv.5)
- `events` — события (Lv.5)
- `arena` — арена (Lv.10)
- `guild` — гильдии (Lv.15)

---

## 6. Gacha Events

### 6.1. gacha_banner_view

Просмотр баннера (открыл экран гачи).

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| banner_id | string | да | ID баннера |
| banner_type | string | да | standard, limited |
| featured_hero_id | string | нет | Featured герой (если limited) |
| player_gems | int | да | Гемов у игрока |
| player_tickets | int | да | Тикетов у игрока |
| can_afford_single | bool | да | Хватает на 1 призыв |
| can_afford_multi | bool | да | Хватает на 10 призывов |

### 6.2. gacha_summon

Призыв героя. Одно событие на каждого призванного героя.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| banner_id | string | да | ID баннера |
| banner_type | string | да | standard, limited |
| summon_type | string | да | single, multi_10 |
| summon_index | int | да | Индекс в мульти-призыве (1-10, для single всегда 1) |
| summon_cost_currency | string | да | gems, summon_tickets |
| summon_cost_amount | int | да | Потрачено (только для первого в мульти) |
| hero_id | string | да | Полученный герой |
| hero_name | string | да | Имя героя |
| hero_rarity | string | да | common, rare, epic, legendary |
| hero_class | string | да | warrior, mage, archer, healer, tank |
| is_new | bool | да | Новый герой (не было раньше) |
| is_duplicate | bool | да | Уже был этот герой |
| is_featured | bool | да | Featured герой баннера |
| pity_counter_before | int | да | Счётчик pity до призыва |
| pity_counter_after | int | да | Счётчик pity после призыва |
| pity_triggered | bool | да | Сработала ли гарантия |

---

## 7. Hero Events

### 7.1. hero_levelup

Повышение уровня героя.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| hero_id | string | да | ID героя |
| hero_name | string | да | Имя героя |
| hero_rarity | string | да | Редкость |
| old_level | int | да | Был уровень |
| new_level | int | да | Стал уровень |
| gold_spent | int | да | Потрачено золота |
| power_before | int | да | Сила до |
| power_after | int | да | Сила после |

### 7.2. hero_ascend

Повышение звёзд героя.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| hero_id | string | да | ID героя |
| hero_name | string | да | Имя героя |
| hero_rarity | string | да | Редкость |
| old_stars | int | да | Было звёзд |
| new_stars | int | да | Стало звёзд |
| duplicates_used | int | да | Потрачено дубликатов |
| power_before | int | да | Сила до |
| power_after | int | да | Сила после |

### 7.3. hero_team_change

Изменение состава отряда.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| old_team | array[string] | да | Предыдущий состав (hero_ids) |
| new_team | array[string] | да | Новый состав |
| team_power_before | int | да | Сила до |
| team_power_after | int | да | Сила после |
| change_reason | string | да | Причина изменения |

**Возможные change_reason:**
- `manual` — ручная замена
- `new_hero` — добавлен новый герой
- `auto_optimize` — авто-подбор

---

## 8. Shop Events

### 8.1. shop_view

Открытие магазина.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| shop_tab | string | да | Какую вкладку открыл |
| player_gems | int | да | Текущий баланс гемов |

**Возможные shop_tab:**
- `iap` — покупки за реальные деньги
- `gems` — покупки за гемы
- `daily` — ежедневные предложения
- `special` — специальные офферы

### 8.2. iap_initiated

Начало покупки (нажал "купить").

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| product_id | string | да | ID продукта |
| product_name | string | да | Название |
| price_usd | float | да | Цена в USD |

### 8.3. iap_purchase

Успешная покупка IAP.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| product_id | string | да | ID продукта |
| product_name | string | да | Название |
| price_usd | float | да | Цена в USD |
| gems_received | int | да | Получено гемов |
| items_received | array[object] | да | Другие предметы |
| is_first_purchase | bool | да | Первая покупка игрока |
| purchase_number | int | да | Номер покупки игрока |
| transaction_id | string | да | ID транзакции |
| vip_points_earned | int | да | Получено VIP очков |

**Формат items_received:**
```json
[
  {"item_id": "summon_ticket", "amount": 10}
]
```

### 8.4. iap_failed

Провал покупки.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| product_id | string | да | ID продукта |
| price_usd | float | да | Цена |
| fail_reason | string | да | Причина провала |

**Возможные fail_reason:**
- `cancelled` — отменено пользователем
- `payment_error` — ошибка оплаты
- `network_error` — сетевая ошибка
- `insufficient_funds` — недостаточно средств

---

## 9. Ads Events

### 9.1. ad_opportunity

Появилась возможность посмотреть рекламу.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| placement | string | да | Размещение |
| ads_watched_today | int | да | Уже просмотрено сегодня |
| ads_available | int | да | Доступно ещё |

**Возможные placement:**
- `main_screen` — главный экран
- `shop` — магазин
- `stage_fail` — после провала уровня
- `energy_refill` — восполнение энергии

### 9.2. ad_started

Начало просмотра рекламы.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| placement | string | да | Размещение |
| ad_network | string | да | Рекламная сеть |

**Возможные ad_network (симуляция):**
- `unity_ads`
- `applovin`
- `ironsource`
- `admob`

### 9.3. ad_completed

Успешный просмотр рекламы.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| placement | string | да | Размещение |
| ad_network | string | да | Рекламная сеть |
| reward_currency | string | да | Валюта награды |
| reward_amount | int | да | Количество |
| watch_duration_sec | int | да | Длительность просмотра |

### 9.4. ad_skipped

Пропуск/закрытие рекламы без награды.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| placement | string | да | Размещение |
| ad_network | string | да | Рекламная сеть |
| skip_after_sec | int | да | Через сколько секунд закрыл |
| skip_reason | string | да | Причина |

**Возможные skip_reason:**
- `user_closed` — закрыл вручную
- `ad_error` — ошибка загрузки
- `timeout` — таймаут

---

## 10. Social Events

### 10.1. arena_battle_start

Начало боя на арене.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| opponent_user_id | string | да | ID противника |
| opponent_power | int | да | Сила противника |
| opponent_rank | int | да | Ранг противника |
| player_power | int | да | Сила игрока |
| player_rank | int | да | Текущий ранг игрока |
| attempt_number | int | да | Номер попытки сегодня |
| is_paid_attempt | bool | да | Платная попытка |

### 10.2. arena_battle_end

Конец боя на арене.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| opponent_user_id | string | да | ID противника |
| result | string | да | win, lose |
| duration_sec | int | да | Длительность |
| rank_before | int | да | Ранг до боя |
| rank_after | int | да | Ранг после боя |
| rating_change | int | да | Изменение рейтинга |
| reward_currency | string | нет | Валюта награды (если win) |
| reward_amount | int | нет | Количество награды |

### 10.3. guild_join

Вступление в гильдию.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| guild_id | string | да | ID гильдии |
| guild_name | string | да | Название |
| guild_member_count | int | да | Участников в гильдии |
| join_method | string | да | Способ вступления |

**Возможные join_method:**
- `search` — нашёл в поиске
- `invite` — по приглашению
- `create` — создал новую

### 10.4. guild_leave

Выход из гильдии.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| guild_id | string | да | ID гильдии |
| guild_name | string | да | Название |
| reason | string | да | Причина выхода |
| days_in_guild | int | да | Дней в гильдии |

**Возможные reason:**
- `voluntary` — добровольный выход
- `kicked` — исключён
- `guild_disbanded` — гильдия распущена

### 10.5. guild_boss_attack

Атака гильд-босса.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| guild_id | string | да | ID гильдии |
| boss_id | string | да | ID босса |
| boss_level | int | да | Уровень босса |
| damage_dealt | int | да | Нанесённый урон |
| team_power | int | да | Сила отряда |
| attempt_number | int | да | Попытка сегодня |
| boss_hp_remaining_pct | float | да | Оставшееся HP босса (%) |

---

## 11. Quest Events

### 11.1. quest_complete

Выполнение квеста.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| quest_id | string | да | ID квеста |
| quest_type | string | да | Тип квеста |
| quest_name | string | да | Название |
| reward_currency | string | да | Валюта награды |
| reward_amount | int | да | Количество |
| time_to_complete_sec | int | нет | Время на выполнение |

**Возможные quest_type:**
- `daily` — ежедневный
- `weekly` — еженедельный
- `achievement` — достижение (разовый)

### 11.2. daily_login

Ежедневный вход (отмечен в календаре).

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| login_streak | int | да | Серия входов подряд |
| reward_day | int | да | День в месячном календаре (1-30) |
| reward_currency | string | да | Валюта награды |
| reward_amount | int | да | Количество |
| is_streak_bonus | bool | да | Бонус за серию |

---

## 12. Event Events (временные активности)

### 12.1. event_start

Игрок начал участие в событии.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| event_id | string | да | ID события |
| event_type | string | да | Тип события |
| event_name | string | да | Название |
| event_start_date | string | да | Дата начала события |
| event_end_date | string | да | Дата окончания |
| days_remaining | int | да | Дней до конца |

**Возможные event_type:**
- `login_event` — бонусы за вход
- `summon_event` — бонусы за призывы
- `spending_event` — бонусы за траты
- `collection_event` — сбор предметов

### 12.2. event_progress

Прогресс в событии.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| event_id | string | да | ID события |
| event_type | string | да | Тип события |
| milestone_reached | int | да | Достигнутая веха |
| milestone_target | int | да | Цель вехи |
| progress_value | int | да | Текущий прогресс |
| reward_claimed | bool | да | Забрана ли награда |
| reward_currency | string | нет | Валюта награды |
| reward_amount | int | нет | Количество |

### 12.3. event_complete

Завершение события (игрок достиг финальной цели).

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| event_id | string | да | ID события |
| event_type | string | да | Тип события |
| total_progress | int | да | Итоговый прогресс |
| milestones_completed | int | да | Вех завершено |
| total_rewards_currency | string | да | Основная валюта наград |
| total_rewards_amount | int | да | Всего получено |

---

## 13. System Events

### 13.1. player_state_snapshot

Ежедневный снимок состояния игрока. Генерируется при первом входе за день.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| snapshot_date | string | да | Дата снапшота (YYYY-MM-DD) |
| player_level | int | да | Уровень игрока |
| vip_level | int | да | VIP уровень |
| total_spent_usd | float | да | Всего потрачено |
| gold_balance | int | да | Баланс золота |
| gems_balance | int | да | Баланс гемов |
| energy_balance | int | да | Баланс энергии |
| summon_tickets_balance | int | да | Баланс тикетов |
| heroes_count | int | да | Количество уникальных героев |
| heroes_by_rarity | object | да | Распределение по редкости |
| max_hero_level | int | да | Максимальный уровень героя |
| max_hero_stars | int | да | Максимальные звёзды героя |
| team_power | int | да | Сила основного отряда |
| max_chapter | int | да | Максимальная глава |
| max_stage | int | да | Максимальный уровень |
| total_stages_cleared | int | да | Всего пройдено уровней (3 звезды) |
| arena_rank | int | нет | Ранг на арене (null если не открыта) |
| arena_rating | int | нет | Рейтинг арены |
| guild_id | string | нет | ID гильдии (null если нет) |
| total_sessions | int | да | Всего сессий |
| total_playtime_sec | int | да | Общее время в игре |
| total_gacha_pulls | int | да | Всего призывов |
| pity_counter | int | да | Текущий счётчик pity |
| last_active_date | string | да | Последняя активность |

**Формат heroes_by_rarity:**
```json
{
  "common": 15,
  "rare": 8,
  "epic": 3,
  "legendary": 1
}
```

### 13.2. tutorial_step

Прохождение шага туториала.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| step_id | string | да | ID шага |
| step_number | int | да | Номер шага (1-N) |
| step_name | string | да | Название |
| duration_sec | int | да | Время на шаг |
| is_skipped | bool | да | Пропущен |

**Шаги туториала:**
| step_id | step_number | step_name |
|---------|-------------|-----------|
| tut_welcome | 1 | Welcome |
| tut_first_battle | 2 | First Battle |
| tut_hero_summon | 3 | Hero Summon |
| tut_hero_levelup | 4 | Hero Level Up |
| tut_team_setup | 5 | Team Setup |
| tut_campaign | 6 | Campaign Intro |
| tut_idle_rewards | 7 | Idle Rewards |
| tut_complete | 8 | Tutorial Complete |

### 13.3. tutorial_complete

Завершение туториала.

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| total_duration_sec | int | да | Общее время туториала |
| steps_completed | int | да | Пройдено шагов |
| steps_skipped | int | да | Пропущено шагов |

### 13.4. error

Ошибка (для симуляции багов логирования).

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| error_type | string | да | Тип ошибки |
| error_code | int | да | Код ошибки |
| error_message | string | да | Сообщение |
| error_context | string | нет | Контекст (какое действие) |

**Возможные error_type:**
- `network_error` — сетевая ошибка
- `validation_error` — ошибка валидации
- `state_error` — ошибка состояния
- `unknown_error` — неизвестная ошибка

---

## 14. Сводная таблица событий

| # | Событие | Категория | Критичность | Частота |
|---|---------|-----------|-------------|---------|
| 1 | session_start | Session | Critical | Каждая сессия |
| 2 | session_end | Session | Critical | Каждая сессия |
| 3 | economy_source | Economy | High | Часто |
| 4 | economy_sink | Economy | High | Часто |
| 5 | stage_start | Progression | Medium | Часто |
| 6 | stage_complete | Progression | High | Часто |
| 7 | stage_fail | Progression | Medium | Средне |
| 8 | idle_reward_claim | Progression | Medium | 1-4/день |
| 9 | player_levelup | Progression | Medium | Редко |
| 10 | gacha_banner_view | Gacha | Low | Средне |
| 11 | gacha_summon | Gacha | High | Средне |
| 12 | hero_levelup | Hero | Medium | Часто |
| 13 | hero_ascend | Hero | Medium | Редко |
| 14 | hero_team_change | Hero | Low | Редко |
| 15 | shop_view | Shop | Low | Средне |
| 16 | iap_initiated | Shop | High | Редко |
| 17 | iap_purchase | Shop | Critical | Редко |
| 18 | iap_failed | Shop | High | Редко |
| 19 | ad_opportunity | Ads | Low | Часто |
| 20 | ad_started | Ads | Medium | Средне |
| 21 | ad_completed | Ads | Medium | Средне |
| 22 | ad_skipped | Ads | Low | Редко |
| 23 | arena_battle_start | Social | Medium | 1-5/день |
| 24 | arena_battle_end | Social | Medium | 1-5/день |
| 25 | guild_join | Social | Medium | Редко |
| 26 | guild_leave | Social | Medium | Редко |
| 27 | guild_boss_attack | Social | Medium | 1/день |
| 28 | quest_complete | Quest | Medium | 5-10/день |
| 29 | daily_login | Quest | Medium | 1/день |
| 30 | event_start | Event | Medium | Редко |
| 31 | event_progress | Event | Medium | Средне |
| 32 | event_complete | Event | Medium | Редко |
| 33 | player_state_snapshot | System | High | 1/день |
| 34 | tutorial_step | System | Medium | Только новые |
| 35 | tutorial_complete | System | Medium | 1 раз |
| 36 | error | System | Low | Симуляция |

**Итого: 36 событий**

---

## 15. Примеры полных событий

### Пример 1: session_start

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440001",
  "event_name": "session_start",
  "event_timestamp": "2025-01-15T14:00:00.000Z",
  "user_id": "u_12345",
  "session_id": "s_abc001",
  "device": {
    "device_id": "d_dev001",
    "platform": "ios",
    "os_version": "17.2",
    "app_version": "1.2.3",
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
    "onboarding_v2": "variant_a"
  },
  "event_properties": {
    "session_number": 47,
    "is_first_session": false,
    "time_since_last_session_sec": 28800,
    "install_source": "organic"
  }
}
```

### Пример 2: gacha_summon

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440002",
  "event_name": "gacha_summon",
  "event_timestamp": "2025-01-15T14:05:32.456Z",
  "user_id": "u_12345",
  "session_id": "s_abc001",
  "device": {
    "device_id": "d_dev001",
    "platform": "ios",
    "os_version": "17.2",
    "app_version": "1.2.3",
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
    "onboarding_v2": "variant_a"
  },
  "event_properties": {
    "banner_id": "limited_fire_hero_202501",
    "banner_type": "limited",
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

### Пример 3: iap_purchase

```json
{
  "event_id": "evt_550e8400-e29b-41d4-a716-446655440003",
  "event_name": "iap_purchase",
  "event_timestamp": "2025-01-15T14:10:15.789Z",
  "user_id": "u_12345",
  "session_id": "s_abc001",
  "device": {
    "device_id": "d_dev001",
    "platform": "ios",
    "os_version": "17.2",
    "app_version": "1.2.3",
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
    "onboarding_v2": "variant_a"
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

---

## 16. Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 0.1 | 2025-02-01 | Первый драфт (33 события) |
| 0.2 | 2025-02-01 | Добавлены Event события (3), поле ab_tests. Итого 36 событий. |
