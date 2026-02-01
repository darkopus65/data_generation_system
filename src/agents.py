"""Agent behavior model for player simulation."""

import hashlib
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from random import Random
from typing import Optional

from .config import SimulationConfig
from .models import (
    AgentState,
    PlayerType,
    Platform,
    HeroRarity,
    DailyQuestProgress,
    generate_user_id,
    generate_device_id,
)


# Session time distribution weights
SESSION_TIME_WEIGHTS = [
    (0, 7, 0.05),    # Night: 5%
    (7, 9, 0.15),    # Morning commute: 15%
    (9, 12, 0.10),   # Work morning: 10%
    (12, 14, 0.20),  # Lunch: 20%
    (14, 18, 0.10),  # Work afternoon: 10%
    (18, 21, 0.25),  # Evening peak: 25%
    (21, 24, 0.15),  # Late evening: 15%
]


def get_ab_group(user_id: str, test_name: str, variants: list, weights: list, seed: int) -> str:
    """Deterministic A/B test group assignment."""
    hash_input = f"{seed}:{test_name}:{user_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

    # Weighted selection
    total = sum(weights)
    normalized_weights = [w / total for w in weights]

    random_value = (hash_value % 10000) / 10000.0
    cumulative = 0.0
    for variant, weight in zip(variants, normalized_weights):
        cumulative += weight
        if random_value < cumulative:
            return variant

    return variants[-1]


class AgentFactory:
    """Factory for creating player agents."""

    def __init__(self, config: SimulationConfig, seed: int):
        self.config = config
        self.seed = seed
        self.agent_counter = 0

    def create_agent(
        self,
        install_date: date,
        install_source: str,
        rng: Random,
        is_bot: bool = False,
    ) -> AgentState:
        """Create a new player agent."""
        self.agent_counter += 1

        user_id = generate_user_id(self.agent_counter)
        device_id = generate_device_id(self.agent_counter)

        # Determine player type
        player_type = self._select_player_type(rng, is_bot)

        # Determine device attributes
        platform, device_model, os_version = self._select_device(rng)
        country = self._select_country(rng)
        app_version = self._select_app_version(rng)
        language = self._get_language_for_country(country)

        # Assign A/B tests
        ab_tests = self._assign_ab_tests(user_id)

        # Create initial state
        agent = AgentState(
            user_id=user_id,
            device_id=device_id,
            agent_type=player_type,
            install_date=install_date,
            install_source=install_source,
            country=country,
            platform=platform,
            device_model=device_model,
            os_version=os_version,
            app_version=app_version,
            language=language,
            ab_tests=ab_tests,
            gold=self.config.initial_gold,
            gems=self.config.initial_gems,
            summon_tickets=self.config.initial_summon_tickets,
            energy=self.config.initial_energy,
            max_energy=self.config.max_energy,
        )

        # Apply source modifiers to create behavioral variations
        source_config = self.config.install_sources.get(install_source, {})
        agent._source_retention_mod = source_config.get("retention_modifier", 1.0)
        agent._source_monetization_mod = source_config.get("monetization_modifier", 1.0)

        # Bot flag
        agent._is_bot = is_bot

        return agent

    def _select_player_type(self, rng: Random, is_bot: bool) -> PlayerType:
        """Select player type based on configuration shares."""
        if is_bot:
            return PlayerType.FREE_CHURNER

        player_types = self.config.player_types
        types = list(player_types.keys())
        shares = [player_types[t]["share"] for t in types]

        value = rng.random()
        cumulative = 0.0
        for pt, share in zip(types, shares):
            cumulative += share
            if value < cumulative:
                return PlayerType(pt)

        return PlayerType(types[-1])

    def _select_device(self, rng: Random) -> tuple[Platform, str, str]:
        """Select platform and device model."""
        platforms = self.config.platform_distribution
        platform_value = rng.random()

        if platform_value < platforms.get("ios", 0.45):
            platform = Platform.IOS
            models = self.config.ios_models
            os_version = f"{rng.randint(15, 17)}.{rng.randint(0, 5)}"
        else:
            platform = Platform.ANDROID
            models = self.config.android_models
            os_version = f"{rng.randint(11, 14)}"

        device_model = rng.choice(models)
        return platform, device_model, os_version

    def _select_country(self, rng: Random) -> str:
        """Select country based on distribution."""
        countries = self.config.country_distribution
        value = rng.random()
        cumulative = 0.0

        for country, share in countries.items():
            cumulative += share
            if value < cumulative:
                return country

        return "other"

    def _select_app_version(self, rng: Random) -> str:
        """Select app version based on weights."""
        versions = self.config.app_versions
        weights = self.config.app_version_weights

        value = rng.random()
        cumulative = 0.0
        for version, weight in zip(versions, weights):
            cumulative += weight
            if value < cumulative:
                return version

        return versions[-1]

    def _get_language_for_country(self, country: str) -> str:
        """Get language code for country."""
        country_to_lang = {
            "RU": "ru",
            "US": "en",
            "DE": "de",
            "BR": "pt",
            "JP": "ja",
            "KR": "ko",
            "other": "en",
        }
        return country_to_lang.get(country, "en")

    def _assign_ab_tests(self, user_id: str) -> dict[str, str]:
        """Assign A/B test variants to user."""
        ab_tests = {}

        for test_name, test_config in self.config.ab_tests.items():
            if not test_config.get("enabled", False):
                continue

            # Check activation condition
            activation = test_config.get("activation_condition")
            if activation and "days_since_install" in activation:
                # This test is activated later, skip for now
                # Will be added dynamically during simulation
                continue

            variants = test_config.get("variants", [])
            weights = test_config.get("weights", [])

            if variants and weights:
                variant = get_ab_group(user_id, test_name, variants, weights, self.seed)
                ab_tests[test_name] = variant

        return ab_tests


class AgentBehavior:
    """Behavior model for player agents."""

    def __init__(self, config: SimulationConfig):
        self.config = config

    def get_retention_probability(
        self,
        agent: AgentState,
        day_since_install: int,
    ) -> float:
        """Calculate probability that agent returns on a given day."""
        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        retention = player_type_config.get("retention", {})

        # Interpolate retention based on day
        if day_since_install == 0:
            return 1.0  # Install day
        elif day_since_install == 1:
            base = retention.get("d1", 0.5)
        elif day_since_install <= 7:
            d1 = retention.get("d1", 0.5)
            d7 = retention.get("d7", 0.2)
            t = (day_since_install - 1) / 6
            base = d1 * (1 - t) + d7 * t
        elif day_since_install <= 30:
            d7 = retention.get("d7", 0.2)
            d30 = retention.get("d30", 0.1)
            t = (day_since_install - 7) / 23
            base = d7 * (1 - t) + d30 * t
        elif day_since_install <= 90:
            d30 = retention.get("d30", 0.1)
            d90 = retention.get("d90", 0.05)
            t = (day_since_install - 30) / 60
            base = d30 * (1 - t) + d90 * t
        else:
            base = retention.get("d90", 0.05) * 0.8  # Further decay

        # Apply modifiers
        modifiers = 1.0

        # Source modifier
        source_mod = getattr(agent, "_source_retention_mod", 1.0)
        modifiers *= source_mod

        # A/B test modifiers
        modifiers *= self._get_ab_retention_modifier(agent, day_since_install)

        # Engagement modifiers
        if agent.consecutive_losses > 3:
            modifiers *= 0.85

        if agent.got_legendary_recently:
            modifiers *= 1.15

        if agent.guild_id:
            modifiers *= 1.10

        # Bot modifier
        if getattr(agent, "_is_bot", False):
            modifiers *= 0.3

        return min(base * modifiers, 0.99)

    def _get_ab_retention_modifier(self, agent: AgentState, day: int) -> float:
        """Get retention modifier from A/B tests."""
        modifier = 1.0

        # Onboarding length test
        onboarding = agent.ab_tests.get("onboarding_length")
        if onboarding:
            effects = self.config.ab_tests.get("onboarding_length", {}).get("effects", {})
            variant_effects = effects.get(onboarding, {})

            if day == 1:
                modifier *= variant_effects.get("d1_retention_mult", 1.0)
            elif day <= 7:
                modifier *= variant_effects.get("d7_retention_mult", 1.0)

        # Late game offer
        late_game = agent.ab_tests.get("late_game_offer")
        if late_game and 30 <= day <= 60:
            effects = self.config.ab_tests.get("late_game_offer", {}).get("effects", {})
            variant_effects = effects.get(late_game, {})
            modifier *= variant_effects.get("d30_d60_retention_mult", 1.0)

        return modifier

    def will_return_today(self, agent: AgentState, current_date: date, rng: Random) -> bool:
        """Decide if agent will return today."""
        if agent.is_churned:
            return False

        day_since_install = (current_date - agent.install_date).days
        prob = self.get_retention_probability(agent, day_since_install)

        return rng.random() < prob

    def get_sessions_count(self, agent: AgentState, current_date: date, rng: Random) -> int:
        """Determine number of sessions for today."""
        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        sessions_range = player_type_config.get("sessions_per_day", [1, 2])

        min_sessions, max_sessions = sessions_range

        # Base sessions (triangular distribution, peak near min)
        base = rng.triangular(min_sessions, max_sessions, min_sessions * 1.2)

        # Weekend bonus
        if current_date.weekday() >= 5:  # Saturday or Sunday
            base *= 1.2

        # A/B test: energy regen rate
        energy_test = agent.ab_tests.get("energy_regen_rate")
        if energy_test:
            effects = self.config.ab_tests.get("energy_regen_rate", {}).get("effects", {})
            variant_effects = effects.get(energy_test, {})
            base *= variant_effects.get("sessions_mult", 1.0)

        # Bot behavior
        if getattr(agent, "_is_bot", False):
            base = rng.randint(1, 2)

        return max(1, round(base))

    def get_session_start_time(self, session_number: int, rng: Random) -> datetime:
        """Generate session start time within a day."""
        # Select time bucket based on weights
        value = rng.random()
        cumulative = 0.0

        for start_hour, end_hour, weight in SESSION_TIME_WEIGHTS:
            cumulative += weight
            if value < cumulative:
                hour = rng.randint(start_hour, end_hour - 1)
                minute = rng.randint(0, 59)
                second = rng.randint(0, 59)
                return datetime(2000, 1, 1, hour, minute, second)

        # Fallback
        return datetime(2000, 1, 1, 12, 0, 0)

    def get_session_duration_minutes(
        self,
        agent: AgentState,
        session_number: int,
        rng: Random,
    ) -> int:
        """Determine session duration in minutes."""
        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        duration_range = player_type_config.get("session_duration_min", [5, 15])

        min_dur, max_dur = duration_range

        # First session of the day is usually longer
        if session_number == 1:
            base = rng.triangular(min_dur, max_dur, max_dur * 0.7)
        else:
            base = rng.triangular(min_dur, max_dur * 0.7, min_dur * 1.3)

        # Bot sessions are short
        if getattr(agent, "_is_bot", False):
            base = rng.randint(2, 5)

        return max(2, round(base))

    def should_do_gacha(self, agent: AgentState, rng: Random) -> bool:
        """Decide if agent should do gacha pulls."""
        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        gacha_desire = player_type_config.get("gacha_desire", 0.3)

        # Check if can afford
        can_afford_single = agent.gems >= self.config.gacha_single_cost or agent.summon_tickets >= 1

        if not can_afford_single:
            return False

        # Base desire
        desire = gacha_desire

        # Pity effect
        if agent.pity_counter >= 75:
            desire += 0.4
        elif agent.pity_counter >= 50:
            desire += 0.2

        # A/B test: pity display
        pity_test = agent.ab_tests.get("gacha_pity_display")
        if pity_test == "visible" and agent.pity_counter >= 50:
            desire += 0.15

        return rng.random() < desire

    def get_gacha_pull_type(self, agent: AgentState, rng: Random) -> dict:
        """Determine gacha pull type (single/multi) and currency."""
        single_cost = self.config.gacha_single_cost
        multi_cost = self.config.gacha_multi_cost

        can_single_ticket = agent.summon_tickets >= 1
        can_multi_ticket = agent.summon_tickets >= 10
        can_single_gems = agent.gems >= single_cost
        can_multi_gems = agent.gems >= multi_cost

        # Prefer tickets over gems
        if can_multi_ticket:
            return {"type": "multi", "currency": "tickets", "count": 10}
        elif can_multi_gems and agent.agent_type in [PlayerType.WHALE, PlayerType.DOLPHIN]:
            return {"type": "multi", "currency": "gems", "count": 10}
        elif can_single_ticket:
            return {"type": "single", "currency": "tickets", "count": 1}
        elif can_single_gems:
            return {"type": "single", "currency": "gems", "count": 1}

        return {"type": "none", "currency": None, "count": 0}

    def roll_gacha(self, agent: AgentState, rng: Random) -> HeroRarity:
        """Roll for hero rarity in gacha."""
        rates = self.config.gacha_rates.copy()

        # Apply pity
        pity = agent.pity_counter
        threshold = self.config.pity_threshold
        soft_start = self.config.soft_pity_start
        boost = self.config.soft_pity_rate_boost

        if pity >= threshold - 1:
            # Hard pity - guaranteed legendary
            return HeroRarity.LEGENDARY

        if pity >= soft_start:
            # Soft pity - boost legendary rate
            boost_amount = (pity - soft_start + 1) * boost
            rates["legendary"] = min(rates["legendary"] + boost_amount, 1.0)

            # Normalize other rates
            remaining = 1.0 - rates["legendary"]
            non_legendary_total = rates["common"] + rates["rare"] + rates["epic"]
            if non_legendary_total > 0:
                factor = remaining / non_legendary_total
                rates["common"] *= factor
                rates["rare"] *= factor
                rates["epic"] *= factor

        # Roll
        value = rng.random()
        cumulative = 0.0

        for rarity_name in ["legendary", "epic", "rare", "common"]:
            cumulative += rates[rarity_name]
            if value < cumulative:
                return HeroRarity(rarity_name)

        return HeroRarity.COMMON

    def should_watch_ad(self, agent: AgentState, rng: Random) -> bool:
        """Decide if agent should watch a rewarded ad."""
        if agent.ads_watched_today >= self.config.max_ads_per_day:
            return False

        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        base_prob = player_type_config.get("ad_watch_probability", 0.5)

        # A/B test: ad reward amount
        ad_test = agent.ab_tests.get("ad_reward_amount")
        if ad_test:
            effects = self.config.ab_tests.get("ad_reward_amount", {}).get("effects", {})
            variant_effects = effects.get(ad_test, {})
            base_prob *= variant_effects.get("ad_watch_mult", 1.0)

        # Less desire if rich in gems
        if agent.gems > 1000:
            base_prob *= 0.7

        return rng.random() < base_prob

    def should_attempt_iap(
        self,
        agent: AgentState,
        trigger: str,
        rng: Random,
    ) -> bool:
        """Decide if agent should attempt an IAP purchase."""
        # Free players rarely convert
        if agent.agent_type in [
            PlayerType.FREE_ENGAGED,
            PlayerType.FREE_CASUAL,
            PlayerType.FREE_CHURNER,
        ]:
            if rng.random() > 0.001:  # 0.1% chance
                return False

        # Base probability by trigger
        trigger_probs = {
            "starter_pack_offer": 0.15,
            "out_of_gems_gacha": 0.08,
            "out_of_energy": 0.03,
            "pity_close": 0.12,
            "limited_banner_ending": 0.10,
            "stuck_progression": 0.05,
            "monthly_pass_reminder": 0.20,
            "late_game_offer": 0.10,
        }

        base_prob = trigger_probs.get(trigger, 0.02)

        # Player type multiplier
        type_mults = {
            PlayerType.WHALE: 3.0,
            PlayerType.DOLPHIN: 1.5,
            PlayerType.MINNOW: 0.8,
            PlayerType.FREE_ENGAGED: 0.1,
            PlayerType.FREE_CASUAL: 0.05,
            PlayerType.FREE_CHURNER: 0.02,
        }
        base_prob *= type_mults.get(agent.agent_type, 1.0)

        # Source monetization modifier
        base_prob *= getattr(agent, "_source_monetization_mod", 1.0)

        # A/B test modifiers
        if trigger == "starter_pack_offer":
            test = agent.ab_tests.get("starter_pack_price")
            if test:
                effects = self.config.ab_tests.get("starter_pack_price", {}).get("effects", {})
                base_prob *= effects.get(test, {}).get("conversion_mult", 1.0)

        if trigger == "late_game_offer":
            test = agent.ab_tests.get("late_game_offer")
            if test:
                effects = self.config.ab_tests.get("late_game_offer", {}).get("effects", {})
                base_prob *= effects.get(test, {}).get("iap_conversion_mult", 1.0)

        # Ad reward A/B test affects IAP
        ad_test = agent.ab_tests.get("ad_reward_amount")
        if ad_test:
            effects = self.config.ab_tests.get("ad_reward_amount", {}).get("effects", {})
            base_prob *= effects.get(ad_test, {}).get("iap_conversion_mult", 1.0)

        return rng.random() < base_prob

    def select_iap_product(self, agent: AgentState, trigger: str, rng: Random) -> str:
        """Select which IAP product to purchase."""
        # Starter pack
        if trigger == "starter_pack_offer" and not agent.bought_starter_pack:
            return "starter_pack"

        # Monthly pass
        if trigger == "monthly_pass_reminder" and not agent.has_active_monthly:
            return "monthly_pass"

        # Gem packs based on player type
        if agent.agent_type == PlayerType.WHALE:
            return rng.choice(["gems_tier4", "gems_tier5"])
        elif agent.agent_type == PlayerType.DOLPHIN:
            return rng.choice(["gems_tier2", "gems_tier3", "gems_tier4"])
        else:
            return rng.choice(["gems_tier1", "gems_tier2"])

    def should_join_guild(self, agent: AgentState, rng: Random) -> bool:
        """Decide if agent should join a guild."""
        if agent.guild_id:
            return False

        if agent.player_level < self.config.feature_unlocks.get("guild", 15):
            return False

        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        engagement = player_type_config.get("guild_engagement", 0.5)

        return rng.random() < engagement * 0.3  # 30% of engagement per day

    def should_do_arena(self, agent: AgentState, rng: Random) -> bool:
        """Decide if agent should do arena battles."""
        if agent.player_level < self.config.feature_unlocks.get("arena", 10):
            return False

        if agent.arena_attempts_today <= 0:
            # Could buy attempts
            if agent.agent_type in [PlayerType.WHALE, PlayerType.DOLPHIN]:
                if agent.gems >= self.config.arena_attempt_cost_gems:
                    return rng.random() < 0.2
            return False

        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        engagement = player_type_config.get("arena_engagement", 0.5)

        return rng.random() < engagement

    def should_attack_guild_boss(self, agent: AgentState, rng: Random) -> bool:
        """Decide if agent should attack guild boss."""
        if not agent.guild_id:
            return False

        if agent.attacked_guild_boss_today:
            return False

        player_type_config = self.config.player_types.get(agent.agent_type.value, {})
        engagement = player_type_config.get("guild_engagement", 0.5)

        return rng.random() < engagement

    def generate_daily_quests(self, agent: AgentState, rng: Random) -> list[DailyQuestProgress]:
        """Generate daily quests for the agent."""
        if agent.player_level < self.config.feature_unlocks.get("daily_quests", 5):
            return []

        quests = [
            DailyQuestProgress("dq_stages", "Complete 5 stages", target=5, current=0),
            DailyQuestProgress("dq_gacha", "Perform 3 summons", target=3, current=0),
            DailyQuestProgress("dq_levelup", "Level up any hero", target=1, current=0),
            DailyQuestProgress("dq_arena", "Win 1 arena battle", target=1, current=0),
            DailyQuestProgress("dq_login", "Log in today", target=1, current=1, completed=True),
        ]

        return quests

    def should_attempt_stage(self, agent: AgentState, required_power: int, rng: Random) -> bool:
        """Decide if agent should attempt a stage."""
        if agent.energy < self.config.stage_energy_cost:
            return False

        power_ratio = agent.team_power / required_power if required_power > 0 else 1.0

        if power_ratio >= 1.2:
            return True
        elif power_ratio >= 1.0:
            return rng.random() < 0.80
        elif power_ratio >= 0.8:
            return rng.random() < 0.40
        else:
            return rng.random() < 0.10

    def simulate_stage_result(
        self,
        agent: AgentState,
        required_power: int,
        rng: Random,
    ) -> tuple[bool, int]:
        """Simulate stage battle result. Returns (success, stars)."""
        power_ratio = agent.team_power / required_power if required_power > 0 else 1.0

        # Success probability
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
            if power_ratio >= 1.3:
                stars = 3
            elif power_ratio >= 1.1:
                stars = 3 if rng.random() < 0.7 else 2
            else:
                stars = rng.choices([1, 2, 3], weights=[0.3, 0.5, 0.2])[0]
            return True, stars
        else:
            return False, 0

    def simulate_arena_result(
        self,
        agent: AgentState,
        opponent_power: int,
        rng: Random,
    ) -> bool:
        """Simulate arena battle result."""
        power_ratio = agent.team_power / opponent_power if opponent_power > 0 else 1.0

        if power_ratio >= 1.2:
            win_prob = 0.85
        elif power_ratio >= 1.0:
            win_prob = 0.60
        elif power_ratio >= 0.8:
            win_prob = 0.35
        else:
            win_prob = 0.15

        return rng.random() < win_prob

    def calculate_arena_rating_change(
        self,
        agent_rating: int,
        opponent_rating: int,
        won: bool,
    ) -> int:
        """Calculate ELO rating change."""
        k = self.config.arena_rating_k_factor
        expected = 1 / (1 + 10 ** ((opponent_rating - agent_rating) / 400))
        actual = 1 if won else 0
        return int(k * (actual - expected))
