"""World state for the game simulation."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from random import Random
from typing import Optional

from .config import SimulationConfig
from .models import (
    Guild,
    GachaBanner,
    GameEvent,
    HeroTemplate,
    HeroRarity,
    HeroClass,
)


# Hero name generators by class
HERO_NAMES = {
    HeroClass.WARRIOR: [
        "Blade Master", "Iron Knight", "Steel Guardian", "War Chief",
        "Battle Titan", "Sword Saint", "Crusader", "Berserker",
        "Champion", "Gladiator", "Warlord", "Paladin",
        "Vanguard", "Sentinel", "Defender", "Conqueror",
        "Ravager", "Slayer", "Reaver", "Destroyer",
    ],
    HeroClass.MAGE: [
        "Frost Witch", "Fire Sage", "Storm Caller", "Archmage",
        "Void Walker", "Crystal Seer", "Shadow Weaver", "Light Bringer",
        "Elementalist", "Enchanter", "Sorcerer", "Wizard",
        "Necromancer", "Illusionist", "Conjurer", "Warlock",
        "Mystic", "Oracle", "Diviner", "Spellbinder",
    ],
    HeroClass.ARCHER: [
        "Eagle Eye", "Swift Arrow", "Wind Runner", "Shadow Hunter",
        "Forest Ranger", "Sniper", "Marksman", "Sharpshooter",
        "Tracker", "Scout", "Pathfinder", "Stalker",
        "Hawk Eye", "Silent Shot", "Death Dealer", "Venomstrike",
        "Crossbow Master", "Bow Master", "Hunter", "Predator",
    ],
    HeroClass.HEALER: [
        "Life Keeper", "Holy Priest", "Light Bearer", "Soul Mender",
        "Nature's Grace", "Divine Touch", "Restoration Master", "Mercy",
        "Cleric", "Bishop", "Saint", "Seraph",
        "Medicine Woman", "Shaman", "Druid", "Herbalist",
        "Angel", "Guardian Spirit", "Beacon", "Hope Bringer",
    ],
    HeroClass.TANK: [
        "Stone Wall", "Iron Fortress", "Shield Bearer", "Mountain Guard",
        "Bulwark", "Rampart", "Bastion", "Colossus",
        "Golem", "Juggernaut", "Behemoth", "Titan",
        "Protector", "Aegis", "Barrier", "Fortress",
        "Earthshaker", "Rock Solid", "Immovable", "Anchor",
    ],
}


@dataclass
class WorldState:
    """Global state of the game world."""

    config: SimulationConfig
    current_date: date
    day_number: int = 1

    # Hero templates (static, generated once)
    hero_templates: dict[str, HeroTemplate] = field(default_factory=dict)

    # Guilds
    guilds: list[Guild] = field(default_factory=list)

    # Gacha banners
    banners: list[GachaBanner] = field(default_factory=list)

    # Active game events
    game_events: list[GameEvent] = field(default_factory=list)

    # Statistics
    total_installs: int = 0
    total_events_generated: int = 0

    def __post_init__(self):
        """Initialize world state."""
        pass

    @classmethod
    def initialize(cls, config: SimulationConfig, rng: Random) -> "WorldState":
        """Create and initialize a new world state."""
        start_date = date.fromisoformat(config.start_date)
        world = cls(config=config, current_date=start_date, day_number=1)

        # Generate hero templates
        world._generate_hero_templates(rng)

        # Generate guilds
        world._generate_guilds(rng)

        # Generate banners
        world._generate_banners(rng)

        # Generate game events
        world._generate_game_events(rng)

        return world

    def _generate_hero_templates(self, rng: Random) -> None:
        """Generate all hero templates."""
        hero_pool = self.config.hero_pool
        base_powers = self.config.hero_base_power
        classes = list(HeroClass)

        for rarity_name, count in hero_pool.items():
            rarity = HeroRarity(rarity_name)
            base_power = base_powers[rarity_name]

            for i in range(1, count + 1):
                hero_id = f"hero_{rarity_name}_{i:03d}"
                hero_class = rng.choice(classes)
                name_pool = HERO_NAMES[hero_class]
                name = rng.choice(name_pool)

                # Make name unique by adding rarity prefix for display
                display_name = f"{name} ({rarity_name.title()})"

                template = HeroTemplate(
                    hero_id=hero_id,
                    name=display_name,
                    rarity=rarity,
                    hero_class=hero_class,
                    base_power=base_power,
                )
                self.hero_templates[hero_id] = template

    def _generate_guilds(self, rng: Random) -> None:
        """Generate all guilds."""
        guild_count = self.config.guild_count
        max_members = self.config.guild_max_members

        guild_prefixes = [
            "Royal", "Shadow", "Dragon", "Phoenix", "Iron",
            "Golden", "Silver", "Dark", "Light", "Storm",
            "Fire", "Ice", "Thunder", "Crystal", "Ancient",
        ]
        guild_suffixes = [
            "Knights", "Legion", "Order", "Guard", "Warriors",
            "Hunters", "Raiders", "Champions", "Defenders", "Alliance",
            "Brigade", "Battalion", "Corps", "Squad", "Force",
        ]

        for i in range(1, guild_count + 1):
            prefix = rng.choice(guild_prefixes)
            suffix = rng.choice(guild_suffixes)
            name = f"{prefix} {suffix}"

            guild = Guild(
                guild_id=f"guild_{i:04d}",
                name=name,
                member_count=0,
                max_members=max_members,
                boss_level=1,
                boss_hp_remaining_pct=100.0,
            )
            self.guilds.append(guild)

    def _generate_banners(self, rng: Random) -> None:
        """Generate gacha banners for the simulation period."""
        start_date = date.fromisoformat(self.config.start_date)
        end_date = start_date + timedelta(days=self.config.duration_days)

        # Standard banner (always active)
        standard_banner = GachaBanner(
            banner_id="standard_banner",
            banner_type="standard",
            featured_hero_id=None,
            start_date=start_date,
            end_date=end_date,
        )
        self.banners.append(standard_banner)

        # Limited banners (rotate every 14 days)
        legendary_heroes = [
            h for h in self.hero_templates.values()
            if h.rarity == HeroRarity.LEGENDARY
        ]

        current = start_date
        banner_num = 1
        while current < end_date:
            featured = rng.choice(legendary_heroes)
            banner_end = min(current + timedelta(days=14), end_date)

            limited_banner = GachaBanner(
                banner_id=f"limited_banner_{banner_num:03d}",
                banner_type="limited",
                featured_hero_id=featured.hero_id,
                start_date=current,
                end_date=banner_end,
            )
            self.banners.append(limited_banner)

            current = banner_end + timedelta(days=1)
            banner_num += 1

    def _generate_game_events(self, rng: Random) -> None:
        """Generate temporary game events for the simulation period."""
        start_date = date.fromisoformat(self.config.start_date)
        end_date = start_date + timedelta(days=self.config.duration_days)

        event_types = ["login_event", "summon_event", "spending_event", "collection_event"]
        event_names = {
            "login_event": ["New Year Celebration", "Spring Festival", "Summer Bash", "Autumn Harvest"],
            "summon_event": ["Hero Festival", "Lucky Draw", "Summoner's Blessing", "Divine Fortune"],
            "spending_event": ["Gem Rush", "Shopping Spree", "Treasure Hunt", "Fortune Fever"],
            "collection_event": ["Artifact Hunt", "Rune Collection", "Fragment Gathering", "Token Chase"],
        }

        # Generate events every 2-3 weeks
        current = start_date + timedelta(days=3)  # First event starts day 3
        event_num = 1

        while current < end_date - timedelta(days=7):
            event_type = event_types[event_num % len(event_types)]
            names = event_names[event_type]
            name = rng.choice(names)

            duration = rng.randint(7, 14)
            event_end = min(current + timedelta(days=duration), end_date)

            # Generate milestones
            milestones = []
            if event_type == "login_event":
                for d in range(1, min(duration + 1, 8)):
                    milestones.append({
                        "day": d,
                        "reward_currency": "gems" if d % 3 == 0 else "gold",
                        "reward_amount": 50 * d if d % 3 == 0 else 500 * d,
                    })
            elif event_type == "summon_event":
                for pulls in [10, 30, 50, 100]:
                    milestones.append({
                        "pulls_required": pulls,
                        "reward_currency": "summon_tickets",
                        "reward_amount": pulls // 10,
                    })
            elif event_type == "spending_event":
                for spend in [5, 20, 50, 100]:
                    milestones.append({
                        "spend_usd": spend,
                        "reward_currency": "gems",
                        "reward_amount": spend * 20,
                    })
            elif event_type == "collection_event":
                for tokens in [100, 300, 500, 1000]:
                    milestones.append({
                        "tokens_required": tokens,
                        "reward_currency": "gems",
                        "reward_amount": tokens // 5,
                    })

            game_event = GameEvent(
                event_id=f"event_{event_num:03d}",
                event_type=event_type,
                event_name=f"{name} #{event_num}",
                start_date=current,
                end_date=event_end,
                milestones=milestones,
            )
            self.game_events.append(game_event)

            # Next event starts 3-7 days after this one ends
            current = event_end + timedelta(days=rng.randint(3, 7))
            event_num += 1

    def advance_day(self) -> None:
        """Advance the world state to the next day."""
        self.current_date += timedelta(days=1)
        self.day_number += 1

        # Reset guild boss HP at the start of each day
        for guild in self.guilds:
            guild.boss_hp_remaining_pct = 100.0

    def get_active_banners(self) -> list[GachaBanner]:
        """Get all active banners for current date."""
        return [b for b in self.banners if b.is_active(self.current_date)]

    def get_active_events(self) -> list[GameEvent]:
        """Get all active game events for current date."""
        return [e for e in self.game_events if e.is_active(self.current_date)]

    def get_limited_banner(self) -> Optional[GachaBanner]:
        """Get the current limited banner, if any."""
        active = self.get_active_banners()
        for banner in active:
            if banner.banner_type == "limited":
                return banner
        return None

    def get_standard_banner(self) -> Optional[GachaBanner]:
        """Get the standard banner."""
        for banner in self.banners:
            if banner.banner_type == "standard":
                return banner
        return None

    def get_hero_template(self, hero_id: str) -> Optional[HeroTemplate]:
        """Get a hero template by ID."""
        return self.hero_templates.get(hero_id)

    def get_heroes_by_rarity(self, rarity: HeroRarity) -> list[HeroTemplate]:
        """Get all hero templates of a specific rarity."""
        return [h for h in self.hero_templates.values() if h.rarity == rarity]

    def get_random_guild(self, rng: Random) -> Optional[Guild]:
        """Get a random guild that has space."""
        available = [g for g in self.guilds if not g.is_full()]
        if available:
            return rng.choice(available)
        return None

    def join_guild(self, guild_id: str) -> bool:
        """Add a member to a guild."""
        for guild in self.guilds:
            if guild.guild_id == guild_id:
                if not guild.is_full():
                    guild.member_count += 1
                    return True
        return False

    def leave_guild(self, guild_id: str) -> bool:
        """Remove a member from a guild."""
        for guild in self.guilds:
            if guild.guild_id == guild_id:
                if guild.member_count > 0:
                    guild.member_count -= 1
                    return True
        return False

    def damage_guild_boss(self, guild_id: str, damage_pct: float) -> float:
        """Deal damage to a guild boss. Returns remaining HP percentage."""
        for guild in self.guilds:
            if guild.guild_id == guild_id:
                guild.boss_hp_remaining_pct = max(0, guild.boss_hp_remaining_pct - damage_pct)
                if guild.boss_hp_remaining_pct <= 0:
                    # Boss defeated, level up
                    guild.boss_level += 1
                    guild.boss_hp_remaining_pct = 100.0
                return guild.boss_hp_remaining_pct
        return 100.0

    def get_stage_power_requirement(self, chapter: int, stage: int) -> int:
        """Calculate power requirement for a stage."""
        stage_num = (chapter - 1) * self.config.stages_per_chapter + stage
        base = self.config.progression.get("stage_power", {}).get("base", 100)
        mult = self.config.progression.get("stage_power", {}).get("per_stage_mult", 1.08)
        return int(base * (mult ** (stage_num - 1)))

    def get_stage_rewards(self, chapter: int, stage: int) -> dict:
        """Calculate rewards for completing a stage."""
        rewards = self.config.economy.get("stage_rewards", {})
        gold_base = rewards.get("gold_base", 100)
        gold_per_chapter = rewards.get("gold_per_chapter", 50)
        exp_base = rewards.get("exp_base", 20)
        exp_per_chapter = rewards.get("exp_per_chapter", 10)

        return {
            "gold": gold_base + (chapter - 1) * gold_per_chapter,
            "exp": exp_base + (chapter - 1) * exp_per_chapter,
        }

    def get_idle_rewards(self, max_stage: int, hours: float) -> dict:
        """Calculate idle rewards based on max stage and time."""
        idle_config = self.config.economy.get("idle_rewards", {})
        gold_per_hour = idle_config.get("gold_per_hour_base", 500)
        stage_mult = idle_config.get("gold_per_stage_mult", 0.05)
        max_hours = idle_config.get("max_hours", 12)

        hours = min(hours, max_hours)
        gold = int(gold_per_hour * (1 + max_stage * stage_mult) * hours)
        exp = int(gold * 0.1)  # 10% of gold as exp

        return {
            "gold": gold,
            "exp": exp,
            "hours": hours,
        }

    def get_levelup_cost(self, current_level: int) -> int:
        """Calculate gold cost to level up a hero."""
        levelup = self.config.economy.get("hero_levelup", {})
        base = levelup.get("gold_base", 100)
        mult = levelup.get("gold_per_level_mult", 1.15)
        return int(base * (mult ** (current_level - 1)))

    def get_exp_for_level(self, level: int) -> int:
        """Calculate exp required for a player level."""
        player_level = self.config.progression.get("player_level", {})
        base = player_level.get("exp_per_level_base", 100)
        mult = player_level.get("exp_per_level_mult", 1.12)
        return int(base * (mult ** (level - 1)))
