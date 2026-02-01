"""Configuration loading and merging for the simulator."""

import copy
from pathlib import Path
from typing import Any, Optional

import yaml


def load_yaml(path: Path) -> dict:
    """Load a YAML configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base config.

    Arrays are replaced, not merged.
    Nested dicts are merged recursively.
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def load_config(
    base_path: Path,
    override_paths: Optional[list[Path]] = None,
) -> dict:
    """Load base config and apply overrides sequentially.

    Args:
        base_path: Path to the base YAML configuration.
        override_paths: Optional list of override YAML files to apply.

    Returns:
        Merged configuration dictionary.
    """
    config = load_yaml(base_path)

    if override_paths:
        for override_path in override_paths:
            override = load_yaml(override_path)
            config = deep_merge(config, override)

    return config


class SimulationConfig:
    """Wrapper for simulation configuration with typed access."""

    def __init__(self, config: dict):
        self._config = config

    @property
    def raw(self) -> dict:
        """Get raw configuration dictionary."""
        return self._config

    # Simulation parameters
    @property
    def seed(self) -> int:
        return self._config["simulation"]["seed"]

    @property
    def start_date(self) -> str:
        return self._config["simulation"]["start_date"]

    @property
    def duration_days(self) -> int:
        return self._config["simulation"]["duration_days"]

    # Install parameters
    @property
    def total_installs(self) -> int:
        return self._config["installs"]["total"]

    @property
    def install_distribution(self) -> str:
        return self._config["installs"]["distribution"]

    @property
    def install_decay_rate(self) -> float:
        return self._config["installs"].get("decay_rate", 0.02)

    @property
    def install_sources(self) -> dict:
        return self._config["installs"]["sources"]

    # Player types
    @property
    def player_types(self) -> dict:
        return self._config["player_types"]

    # Economy
    @property
    def economy(self) -> dict:
        return self._config["economy"]

    @property
    def initial_gold(self) -> int:
        return self._config["economy"]["initial"]["gold"]

    @property
    def initial_gems(self) -> int:
        return self._config["economy"]["initial"]["gems"]

    @property
    def initial_summon_tickets(self) -> int:
        return self._config["economy"]["initial"]["summon_tickets"]

    @property
    def initial_energy(self) -> int:
        return self._config["economy"]["initial"]["energy"]

    @property
    def max_energy(self) -> int:
        return self._config["economy"]["energy"]["max"]

    @property
    def energy_regen_minutes(self) -> int:
        return self._config["economy"]["energy"]["regen_minutes"]

    @property
    def stage_energy_cost(self) -> int:
        return self._config["economy"]["energy"]["stage_cost"]

    # Gacha
    @property
    def gacha(self) -> dict:
        return self._config["gacha"]

    @property
    def gacha_single_cost(self) -> int:
        return self._config["gacha"]["single_gems"]

    @property
    def gacha_multi_cost(self) -> int:
        return self._config["gacha"]["multi_gems"]

    @property
    def gacha_rates(self) -> dict:
        return self._config["gacha"]["rates"]

    @property
    def pity_threshold(self) -> int:
        return self._config["gacha"]["pity"]["threshold"]

    @property
    def soft_pity_start(self) -> int:
        return self._config["gacha"]["pity"]["soft_pity_start"]

    @property
    def soft_pity_rate_boost(self) -> float:
        return self._config["gacha"]["pity"]["soft_pity_rate_boost"]

    # Shop
    @property
    def shop_products(self) -> dict:
        return self._config["shop"]["products"]

    @property
    def ad_reward_gems(self) -> int:
        return self._config["shop"]["ads"]["reward_gems"]

    @property
    def max_ads_per_day(self) -> int:
        return self._config["shop"]["ads"]["max_per_day"]

    @property
    def ad_cooldown_minutes(self) -> int:
        return self._config["shop"]["ads"]["cooldown_minutes"]

    # VIP
    @property
    def vip_levels(self) -> dict:
        return self._config["vip"]["levels"]

    # Progression
    @property
    def progression(self) -> dict:
        return self._config["progression"]

    @property
    def total_chapters(self) -> int:
        return self._config["progression"]["chapters"]

    @property
    def stages_per_chapter(self) -> int:
        return self._config["progression"]["stages_per_chapter"]

    @property
    def feature_unlocks(self) -> dict:
        return self._config["progression"]["unlocks"]

    # Heroes
    @property
    def heroes(self) -> dict:
        return self._config["heroes"]

    @property
    def hero_pool(self) -> dict:
        return self._config["heroes"]["pool"]

    @property
    def hero_base_power(self) -> dict:
        return self._config["heroes"]["base_power"]

    # Social
    @property
    def social(self) -> dict:
        return self._config["social"]

    @property
    def arena_daily_attempts(self) -> int:
        return self._config["social"]["arena"]["daily_attempts"]

    @property
    def arena_attempt_cost_gems(self) -> int:
        return self._config["social"]["arena"]["attempt_cost_gems"]

    @property
    def arena_rating_start(self) -> int:
        return self._config["social"]["arena"]["rating_start"]

    @property
    def arena_rating_k_factor(self) -> int:
        return self._config["social"]["arena"]["rating_k_factor"]

    @property
    def guild_count(self) -> int:
        return self._config["social"]["guilds"]["count"]

    @property
    def guild_max_members(self) -> int:
        return self._config["social"]["guilds"]["max_members"]

    # A/B Tests
    @property
    def ab_tests(self) -> dict:
        return self._config.get("ab_tests", {})

    # Scenarios
    @property
    def scenarios(self) -> dict:
        return self._config.get("scenarios", {})

    @property
    def bad_traffic_config(self) -> Optional[dict]:
        scenarios = self.scenarios
        if scenarios.get("bad_traffic", {}).get("enabled", False):
            return scenarios["bad_traffic"]
        return None

    # Output
    @property
    def output_format(self) -> str:
        return self._config["output"]["format"]

    @property
    def output_compression(self) -> str:
        return self._config["output"]["compression"]

    @property
    def output_batch_size(self) -> int:
        return self._config["output"]["batch_size"]

    @property
    def include_metadata(self) -> bool:
        return self._config["output"]["include_metadata"]

    # Devices
    @property
    def devices(self) -> dict:
        return self._config["devices"]

    @property
    def platform_distribution(self) -> dict:
        return self._config["devices"]["platforms"]

    @property
    def country_distribution(self) -> dict:
        return self._config["devices"]["countries"]

    @property
    def ios_models(self) -> list:
        return self._config["devices"]["ios_models"]

    @property
    def android_models(self) -> list:
        return self._config["devices"]["android_models"]

    @property
    def app_versions(self) -> list:
        return self._config["devices"]["app_versions"]

    @property
    def app_version_weights(self) -> list:
        return self._config["devices"]["app_version_weights"]

    def get_ab_test_config(self, test_name: str) -> Optional[dict]:
        """Get configuration for a specific A/B test."""
        return self.ab_tests.get(test_name)

    def is_ab_test_enabled(self, test_name: str) -> bool:
        """Check if an A/B test is enabled."""
        test_config = self.get_ab_test_config(test_name)
        if test_config:
            return test_config.get("enabled", False)
        return False

    def get_vip_level_for_spend(self, total_spent: float) -> int:
        """Get VIP level for a given total spend amount."""
        current_level = 0
        for level, data in self.vip_levels.items():
            level_int = int(level)
            threshold = data["threshold"]
            if total_spent >= threshold and level_int > current_level:
                current_level = level_int
        return current_level

    def get_vip_bonuses(self, vip_level: int) -> dict:
        """Get bonuses for a VIP level."""
        level_data = self.vip_levels.get(str(vip_level), {})
        return {
            "energy_bonus": level_data.get("energy_bonus", 0),
            "gold_bonus": level_data.get("gold_bonus", 0),
        }
