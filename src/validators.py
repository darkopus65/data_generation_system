"""Configuration validators for the simulator."""

from typing import Optional


class ValidationError(Exception):
    """Configuration validation error."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Configuration validation failed: {errors}")


class ConfigValidator:
    """Validator for simulation configuration."""

    def __init__(self, config: dict):
        self.config = config
        self.errors: list[str] = []

    def validate(self) -> list[str]:
        """Run all validations and return list of errors."""
        self.errors = []

        self._validate_required_sections()
        self._validate_simulation_params()
        self._validate_player_type_shares()
        self._validate_install_source_shares()
        self._validate_retention_order()
        self._validate_platform_shares()
        self._validate_country_shares()
        self._validate_gacha_rates()
        self._validate_ab_test_weights()
        self._validate_references()
        self._validate_numeric_ranges()

        return self.errors

    def validate_or_raise(self) -> None:
        """Run validation and raise exception if errors found."""
        errors = self.validate()
        if errors:
            raise ValidationError(errors)

    def _validate_required_sections(self) -> None:
        """Check that all required top-level sections exist."""
        required_sections = [
            "simulation",
            "installs",
            "player_types",
            "economy",
            "gacha",
            "shop",
            "vip",
            "progression",
            "heroes",
            "social",
            "output",
            "devices",
        ]
        for section in required_sections:
            if section not in self.config:
                self.errors.append(f"Missing required section: {section}")

    def _validate_simulation_params(self) -> None:
        """Validate simulation parameters."""
        sim = self.config.get("simulation", {})

        if "seed" not in sim:
            self.errors.append("simulation.seed is required")
        elif not isinstance(sim["seed"], int):
            self.errors.append("simulation.seed must be an integer")

        if "start_date" not in sim:
            self.errors.append("simulation.start_date is required")

        if "duration_days" not in sim:
            self.errors.append("simulation.duration_days is required")
        elif not isinstance(sim["duration_days"], int) or sim["duration_days"] < 1:
            self.errors.append("simulation.duration_days must be a positive integer")
        elif sim["duration_days"] > 365:
            self.errors.append("simulation.duration_days must be <= 365")

    def _validate_share_sum(
        self,
        data: dict,
        path: str,
        expected_sum: float = 1.0,
        tolerance: float = 0.01,
    ) -> None:
        """Validate that shares in a dictionary sum to expected value."""
        total = 0.0
        for key, value in data.items():
            if isinstance(value, dict) and "share" in value:
                total += value["share"]
            elif isinstance(value, (int, float)):
                total += value

        if abs(total - expected_sum) > tolerance:
            self.errors.append(
                f"{path} shares sum to {total:.4f}, expected {expected_sum}"
            )

    def _validate_player_type_shares(self) -> None:
        """Validate player type shares sum to 1.0."""
        player_types = self.config.get("player_types", {})
        self._validate_share_sum(player_types, "player_types")

    def _validate_install_source_shares(self) -> None:
        """Validate install source shares sum to 1.0."""
        sources = self.config.get("installs", {}).get("sources", {})
        self._validate_share_sum(sources, "installs.sources")

    def _validate_platform_shares(self) -> None:
        """Validate platform shares sum to 1.0."""
        platforms = self.config.get("devices", {}).get("platforms", {})
        if platforms:
            total = sum(platforms.values())
            if abs(total - 1.0) > 0.01:
                self.errors.append(
                    f"devices.platforms shares sum to {total:.4f}, expected 1.0"
                )

    def _validate_country_shares(self) -> None:
        """Validate country shares sum to 1.0."""
        countries = self.config.get("devices", {}).get("countries", {})
        if countries:
            total = sum(countries.values())
            if abs(total - 1.0) > 0.01:
                self.errors.append(
                    f"devices.countries shares sum to {total:.4f}, expected 1.0"
                )

    def _validate_gacha_rates(self) -> None:
        """Validate gacha rates sum to 1.0."""
        rates = self.config.get("gacha", {}).get("rates", {})
        if rates:
            total = sum(rates.values())
            if abs(total - 1.0) > 0.01:
                self.errors.append(
                    f"gacha.rates sum to {total:.4f}, expected 1.0"
                )

    def _validate_retention_order(self) -> None:
        """Validate that retention decreases over time for each player type."""
        player_types = self.config.get("player_types", {})

        for name, pt in player_types.items():
            ret = pt.get("retention", {})
            d1 = ret.get("d1", 1.0)
            d7 = ret.get("d7", 0.0)
            d30 = ret.get("d30", 0.0)
            d90 = ret.get("d90", 0.0)

            if not (d1 >= d7 >= d30 >= d90):
                self.errors.append(
                    f"player_type '{name}': retention must be d1 >= d7 >= d30 >= d90 "
                    f"(got d1={d1}, d7={d7}, d30={d30}, d90={d90})"
                )

            # Validate ranges
            for day, value in [("d1", d1), ("d7", d7), ("d30", d30), ("d90", d90)]:
                if not (0 <= value <= 1):
                    self.errors.append(
                        f"player_type '{name}': retention.{day} must be between 0 and 1"
                    )

    def _validate_ab_test_weights(self) -> None:
        """Validate A/B test variant weights sum to 1.0."""
        ab_tests = self.config.get("ab_tests", {})

        for test_name, test_config in ab_tests.items():
            if not test_config.get("enabled", False):
                continue

            variants = test_config.get("variants", [])
            weights = test_config.get("weights", [])

            if len(variants) != len(weights):
                self.errors.append(
                    f"ab_tests.{test_name}: variants and weights must have same length"
                )
                continue

            total = sum(weights)
            if abs(total - 1.0) > 0.01:
                self.errors.append(
                    f"ab_tests.{test_name}: weights sum to {total:.4f}, expected 1.0"
                )

    def _validate_references(self) -> None:
        """Validate cross-references in configuration."""
        unlocks = self.config.get("progression", {}).get("unlocks", {})
        max_level = self.config.get("progression", {}).get("player_level", {}).get("max", 100)

        for feature, level in unlocks.items():
            if level > max_level:
                self.errors.append(
                    f"progression.unlocks.{feature} ({level}) > player_level.max ({max_level})"
                )

    def _validate_numeric_ranges(self) -> None:
        """Validate numeric values are in reasonable ranges."""
        installs = self.config.get("installs", {})
        if "total" in installs:
            if installs["total"] < 100:
                self.errors.append("installs.total should be at least 100")
            if installs["total"] > 10_000_000:
                self.errors.append("installs.total should be at most 10,000,000")

        gacha = self.config.get("gacha", {})
        pity = gacha.get("pity", {})
        if pity:
            threshold = pity.get("threshold", 90)
            soft_start = pity.get("soft_pity_start", 75)
            if soft_start >= threshold:
                self.errors.append(
                    f"gacha.pity.soft_pity_start ({soft_start}) must be < threshold ({threshold})"
                )

        # Validate VIP thresholds are increasing
        vip_levels = self.config.get("vip", {}).get("levels", {})
        prev_threshold = -1
        for level in sorted(vip_levels.keys(), key=int):
            threshold = vip_levels[level].get("threshold", 0)
            if threshold < prev_threshold:
                self.errors.append(
                    f"vip.levels.{level}.threshold ({threshold}) must be >= previous level"
                )
            prev_threshold = threshold


def validate_config(config: dict) -> list[str]:
    """Validate configuration and return list of errors."""
    validator = ConfigValidator(config)
    return validator.validate()


def validate_config_or_raise(config: dict) -> None:
    """Validate configuration and raise exception if errors found."""
    validator = ConfigValidator(config)
    validator.validate_or_raise()
