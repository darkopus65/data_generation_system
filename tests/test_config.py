"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path

from src.config import load_config, deep_merge, SimulationConfig
from src.validators import validate_config, ConfigValidator


class TestConfigLoading:
    """Tests for config loading functions."""

    def test_deep_merge_simple(self):
        """Test simple deep merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test deep merge with nested dicts."""
        base = {
            "level1": {
                "level2": {
                    "a": 1,
                    "b": 2,
                }
            }
        }
        override = {
            "level1": {
                "level2": {
                    "b": 3,
                    "c": 4,
                }
            }
        }
        result = deep_merge(base, override)

        assert result["level1"]["level2"] == {"a": 1, "b": 3, "c": 4}

    def test_load_default_config(self):
        """Test loading default config."""
        config_path = Path("configs/default.yaml")
        if config_path.exists():
            config = load_config(config_path)
            assert "simulation" in config
            assert "player_types" in config
            assert config["simulation"]["seed"] == 42


class TestValidation:
    """Tests for config validation."""

    def test_valid_config(self):
        """Test that default config is valid."""
        config_path = Path("configs/default.yaml")
        if config_path.exists():
            config = load_config(config_path)
            errors = validate_config(config)
            assert errors == [], f"Errors found: {errors}"

    def test_player_type_share_sum(self):
        """Test that player type shares must sum to 1."""
        config = {
            "simulation": {"seed": 42, "start_date": "2025-01-01", "duration_days": 7},
            "installs": {"total": 100, "distribution": "uniform", "sources": {"organic": {"share": 1.0}}},
            "player_types": {
                "type1": {"share": 0.5, "retention": {"d1": 0.5, "d7": 0.3, "d30": 0.1}},
                "type2": {"share": 0.3, "retention": {"d1": 0.5, "d7": 0.3, "d30": 0.1}},
            },
            "economy": {"initial": {"gold": 0, "gems": 0, "summon_tickets": 0, "energy": 0}},
            "gacha": {"rates": {"common": 1.0}},
            "shop": {},
            "vip": {"levels": {}},
            "progression": {},
            "heroes": {},
            "social": {},
            "output": {},
            "devices": {},
        }

        validator = ConfigValidator(config)
        errors = validator.validate()

        # Should have error about shares not summing to 1
        share_errors = [e for e in errors if "shares sum to" in e]
        assert len(share_errors) > 0

    def test_retention_order_validation(self):
        """Test that retention must decrease over time."""
        config = {
            "simulation": {"seed": 42, "start_date": "2025-01-01", "duration_days": 7},
            "installs": {"total": 100, "distribution": "uniform", "sources": {"organic": {"share": 1.0}}},
            "player_types": {
                "bad_type": {
                    "share": 1.0,
                    "retention": {
                        "d1": 0.5,
                        "d7": 0.8,  # Wrong: higher than d1
                        "d30": 0.3,
                    }
                },
            },
            "economy": {"initial": {"gold": 0, "gems": 0, "summon_tickets": 0, "energy": 0}},
            "gacha": {"rates": {"common": 1.0}},
            "shop": {},
            "vip": {"levels": {}},
            "progression": {},
            "heroes": {},
            "social": {},
            "output": {},
            "devices": {},
        }

        validator = ConfigValidator(config)
        errors = validator.validate()

        retention_errors = [e for e in errors if "retention must be" in e]
        assert len(retention_errors) > 0


class TestSimulationConfig:
    """Tests for SimulationConfig wrapper."""

    def test_config_properties(self):
        """Test config wrapper properties."""
        config_dict = {
            "simulation": {"seed": 123, "start_date": "2025-01-01", "duration_days": 30},
            "installs": {"total": 1000},
            "output": {"format": "jsonl"},
        }
        config = SimulationConfig(config_dict)

        assert config.seed == 123
        assert config.start_date == "2025-01-01"
        assert config.duration_days == 30
        assert config.total_installs == 1000
        assert config.output_format == "jsonl"
