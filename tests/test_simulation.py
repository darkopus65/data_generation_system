"""Tests for the simulation engine."""

import gzip
import json
import tempfile
from pathlib import Path
from random import Random

import pytest

from src.config import load_config, SimulationConfig
from src.simulation import Simulator
from src.writers import OutputManager
from src.world import WorldState
from src.agents import AgentFactory, AgentBehavior
from src.models import HeroRarity


class TestWorldState:
    """Tests for world state initialization."""

    def test_world_initialization(self):
        """Test that world initializes correctly."""
        config_path = Path("configs/default.yaml")
        if not config_path.exists():
            pytest.skip("Default config not found")

        config_dict = load_config(config_path)
        config = SimulationConfig(config_dict)
        rng = Random(42)

        world = WorldState.initialize(config, rng)

        # Check hero templates
        assert len(world.hero_templates) > 0
        assert len(world.get_heroes_by_rarity(HeroRarity.LEGENDARY)) == 5
        assert len(world.get_heroes_by_rarity(HeroRarity.EPIC)) == 10

        # Check guilds
        assert len(world.guilds) == config.guild_count

        # Check banners
        assert len(world.banners) > 0
        standard = world.get_standard_banner()
        assert standard is not None
        assert standard.banner_type == "standard"


class TestAgentFactory:
    """Tests for agent creation."""

    def test_agent_creation(self):
        """Test creating a new agent."""
        config_path = Path("configs/default.yaml")
        if not config_path.exists():
            pytest.skip("Default config not found")

        config_dict = load_config(config_path)
        config = SimulationConfig(config_dict)
        factory = AgentFactory(config, seed=42)
        rng = Random(42)

        from datetime import date
        agent = factory.create_agent(
            install_date=date(2025, 1, 1),
            install_source="organic",
            rng=rng,
        )

        assert agent.user_id == "u_000001"
        assert agent.device_id == "d_000001"
        assert agent.install_source == "organic"
        assert agent.gold == config.initial_gold
        assert agent.gems == config.initial_gems
        assert agent.energy == config.initial_energy


class TestSimulationDeterminism:
    """Tests for simulation reproducibility."""

    def test_determinism(self):
        """Test that same seed produces same output (excluding UUIDs)."""
        config_path = Path("configs/default.yaml")
        override_path = Path("configs/overrides/small_test.yaml")

        if not config_path.exists() or not override_path.exists():
            pytest.skip("Config files not found")

        config_dict = load_config(config_path, [override_path])
        config = SimulationConfig(config_dict)

        results = []

        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmpdir:
                output_dir = Path(tmpdir) / "output"
                output_manager = OutputManager(
                    output_dir=output_dir,
                    output_format="jsonl",
                    compression="gzip",
                    batch_size=1000,
                    include_metadata=True,
                )

                with output_manager:
                    simulator = Simulator(config, output_manager)
                    simulator.run()
                    from datetime import datetime
                    output_manager.finalize("2025-01-07", datetime.now())

                # Read first few events
                events_file = output_dir / "events.jsonl.gz"
                with gzip.open(events_file, "rt") as f:
                    first_events = [json.loads(line) for line in f.readlines()[:10]]

                # Remove non-deterministic fields (UUIDs)
                for event in first_events:
                    event.pop("event_id", None)
                    event.pop("session_id", None)

                results.append(first_events)

        # Compare
        assert len(results) == 2
        assert results[0] == results[1], "Simulation is not deterministic"


class TestAgentBehavior:
    """Tests for agent behavior model."""

    def test_retention_probability(self):
        """Test retention probability calculation."""
        config_path = Path("configs/default.yaml")
        if not config_path.exists():
            pytest.skip("Default config not found")

        config_dict = load_config(config_path)
        config = SimulationConfig(config_dict)
        behavior = AgentBehavior(config)
        factory = AgentFactory(config, seed=42)
        rng = Random(42)

        from datetime import date
        agent = factory.create_agent(
            install_date=date(2025, 1, 1),
            install_source="organic",
            rng=rng,
        )

        # Day 0 should be 100%
        prob_d0 = behavior.get_retention_probability(agent, 0)
        assert prob_d0 == 1.0

        # Day 1 should be less than 100%
        prob_d1 = behavior.get_retention_probability(agent, 1)
        assert prob_d1 < 1.0

        # Retention should decrease over time
        prob_d7 = behavior.get_retention_probability(agent, 7)
        prob_d30 = behavior.get_retention_probability(agent, 30)

        assert prob_d1 >= prob_d7 >= prob_d30

    def test_gacha_roll(self):
        """Test gacha roll mechanics."""
        config_path = Path("configs/default.yaml")
        if not config_path.exists():
            pytest.skip("Default config not found")

        config_dict = load_config(config_path)
        config = SimulationConfig(config_dict)
        behavior = AgentBehavior(config)
        factory = AgentFactory(config, seed=42)
        rng = Random(42)

        from datetime import date
        agent = factory.create_agent(
            install_date=date(2025, 1, 1),
            install_source="organic",
            rng=rng,
        )

        # Roll many times and check distribution
        results = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
        for _ in range(1000):
            rarity = behavior.roll_gacha(agent, rng)
            results[rarity.value] += 1
            agent.pity_counter += 1
            if rarity == HeroRarity.LEGENDARY:
                agent.pity_counter = 0

        # Common should be most frequent
        assert results["common"] > results["rare"]
        assert results["rare"] > results["epic"]
        # At least some legendary due to pity
        assert results["legendary"] > 0
