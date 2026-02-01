"""Event generation for all 36 event types."""

from datetime import datetime, date
from random import Random
from typing import Optional

from .models import (
    Event,
    AgentState,
    HeroInstance,
    HeroTemplate,
    GachaBanner,
    Guild,
    GameEvent,
    generate_event_id,
    generate_transaction_id,
)


class EventEmitter:
    """Generates events for all game actions."""

    def __init__(self):
        self.events: list[Event] = []

    def clear(self) -> None:
        """Clear accumulated events."""
        self.events = []

    def get_events(self) -> list[Event]:
        """Get all accumulated events."""
        return self.events

    def _create_event(
        self,
        event_name: str,
        timestamp: datetime,
        agent: AgentState,
        current_date: date,
        event_properties: dict,
    ) -> Event:
        """Create a base event with common fields."""
        event = Event(
            event_id=generate_event_id(),
            event_name=event_name,
            event_timestamp=timestamp,
            user_id=agent.user_id,
            session_id=agent.current_session_id or "",
            device=agent.get_device_info(),
            user_properties=agent.get_user_properties(current_date),
            ab_tests=agent.ab_tests.copy(),
            event_properties=event_properties,
        )
        self.events.append(event)
        return event

    # =========================================================================
    # SESSION EVENTS
    # =========================================================================

    def emit_session_start(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        session_number: int,
        is_first_session: bool,
        time_since_last_session_sec: Optional[int],
    ) -> Event:
        """Emit session_start event."""
        return self._create_event(
            "session_start",
            timestamp,
            agent,
            current_date,
            {
                "session_number": session_number,
                "is_first_session": is_first_session,
                "time_since_last_session_sec": time_since_last_session_sec,
                "install_source": agent.install_source,
            },
        )

    def emit_session_end(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        session_duration_sec: int,
        events_count: int,
        stages_played: int,
        gems_spent: int,
        gold_spent: int,
    ) -> Event:
        """Emit session_end event."""
        return self._create_event(
            "session_end",
            timestamp,
            agent,
            current_date,
            {
                "session_duration_sec": session_duration_sec,
                "events_count": events_count,
                "stages_played": stages_played,
                "gems_spent": gems_spent,
                "gold_spent": gold_spent,
            },
        )

    # =========================================================================
    # ECONOMY EVENTS
    # =========================================================================

    def emit_economy_source(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        currency: str,
        amount: int,
        balance_after: int,
        source: str,
        source_id: Optional[str] = None,
    ) -> Event:
        """Emit economy_source event (currency gained)."""
        props = {
            "currency": currency,
            "amount": amount,
            "balance_after": balance_after,
            "source": source,
        }
        if source_id:
            props["source_id"] = source_id
        return self._create_event("economy_source", timestamp, agent, current_date, props)

    def emit_economy_sink(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        currency: str,
        amount: int,
        balance_after: int,
        sink: str,
        sink_id: Optional[str] = None,
    ) -> Event:
        """Emit economy_sink event (currency spent)."""
        props = {
            "currency": currency,
            "amount": amount,
            "balance_after": balance_after,
            "sink": sink,
        }
        if sink_id:
            props["sink_id"] = sink_id
        return self._create_event("economy_sink", timestamp, agent, current_date, props)

    # =========================================================================
    # PROGRESSION EVENTS
    # =========================================================================

    def emit_stage_start(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        chapter: int,
        stage: int,
        attempt_number: int,
        team_power: int,
        team_size: int,
        hero_ids: list[str],
    ) -> Event:
        """Emit stage_start event."""
        stage_id = f"ch{chapter:02d}_st{stage:02d}"
        return self._create_event(
            "stage_start",
            timestamp,
            agent,
            current_date,
            {
                "chapter": chapter,
                "stage": stage,
                "stage_id": stage_id,
                "attempt_number": attempt_number,
                "team_power": team_power,
                "team_size": team_size,
                "hero_ids": hero_ids,
            },
        )

    def emit_stage_complete(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        chapter: int,
        stage: int,
        duration_sec: int,
        stars: int,
        is_first_clear: bool,
        gold_reward: int,
        exp_reward: int,
        loot_items: list[dict],
    ) -> Event:
        """Emit stage_complete event."""
        stage_id = f"ch{chapter:02d}_st{stage:02d}"
        return self._create_event(
            "stage_complete",
            timestamp,
            agent,
            current_date,
            {
                "chapter": chapter,
                "stage": stage,
                "stage_id": stage_id,
                "duration_sec": duration_sec,
                "stars": stars,
                "is_first_clear": is_first_clear,
                "gold_reward": gold_reward,
                "exp_reward": exp_reward,
                "loot_items": loot_items,
            },
        )

    def emit_stage_fail(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        chapter: int,
        stage: int,
        duration_sec: int,
        fail_reason: str,
        team_power: int,
        required_power: int,
    ) -> Event:
        """Emit stage_fail event."""
        stage_id = f"ch{chapter:02d}_st{stage:02d}"
        return self._create_event(
            "stage_fail",
            timestamp,
            agent,
            current_date,
            {
                "chapter": chapter,
                "stage": stage,
                "stage_id": stage_id,
                "duration_sec": duration_sec,
                "fail_reason": fail_reason,
                "team_power": team_power,
                "required_power": required_power,
            },
        )

    def emit_idle_reward_claim(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        idle_duration_sec: int,
        gold_earned: int,
        exp_earned: int,
        max_stage_id: str,
    ) -> Event:
        """Emit idle_reward_claim event."""
        return self._create_event(
            "idle_reward_claim",
            timestamp,
            agent,
            current_date,
            {
                "idle_duration_sec": idle_duration_sec,
                "gold_earned": gold_earned,
                "exp_earned": exp_earned,
                "max_stage_id": max_stage_id,
            },
        )

    def emit_player_levelup(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        old_level: int,
        new_level: int,
        unlocked_features: list[str],
    ) -> Event:
        """Emit player_levelup event."""
        return self._create_event(
            "player_levelup",
            timestamp,
            agent,
            current_date,
            {
                "old_level": old_level,
                "new_level": new_level,
                "unlocked_features": unlocked_features,
            },
        )

    # =========================================================================
    # GACHA EVENTS
    # =========================================================================

    def emit_gacha_banner_view(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        banner: GachaBanner,
        player_gems: int,
        player_tickets: int,
        can_afford_single: bool,
        can_afford_multi: bool,
    ) -> Event:
        """Emit gacha_banner_view event."""
        return self._create_event(
            "gacha_banner_view",
            timestamp,
            agent,
            current_date,
            {
                "banner_id": banner.banner_id,
                "banner_type": banner.banner_type,
                "featured_hero_id": banner.featured_hero_id,
                "player_gems": player_gems,
                "player_tickets": player_tickets,
                "can_afford_single": can_afford_single,
                "can_afford_multi": can_afford_multi,
            },
        )

    def emit_gacha_summon(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        banner: GachaBanner,
        summon_type: str,
        summon_index: int,
        summon_cost_currency: str,
        summon_cost_amount: int,
        hero: HeroTemplate,
        is_new: bool,
        is_duplicate: bool,
        pity_counter_before: int,
        pity_counter_after: int,
        pity_triggered: bool,
    ) -> Event:
        """Emit gacha_summon event."""
        return self._create_event(
            "gacha_summon",
            timestamp,
            agent,
            current_date,
            {
                "banner_id": banner.banner_id,
                "banner_type": banner.banner_type,
                "summon_type": summon_type,
                "summon_index": summon_index,
                "summon_cost_currency": summon_cost_currency,
                "summon_cost_amount": summon_cost_amount,
                "hero_id": hero.hero_id,
                "hero_name": hero.name,
                "hero_rarity": hero.rarity.value,
                "hero_class": hero.hero_class.value,
                "is_new": is_new,
                "is_duplicate": is_duplicate,
                "is_featured": hero.hero_id == banner.featured_hero_id,
                "pity_counter_before": pity_counter_before,
                "pity_counter_after": pity_counter_after,
                "pity_triggered": pity_triggered,
            },
        )

    # =========================================================================
    # HERO EVENTS
    # =========================================================================

    def emit_hero_levelup(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        hero: HeroInstance,
        old_level: int,
        new_level: int,
        gold_spent: int,
        power_before: int,
        power_after: int,
    ) -> Event:
        """Emit hero_levelup event."""
        return self._create_event(
            "hero_levelup",
            timestamp,
            agent,
            current_date,
            {
                "hero_id": hero.hero_id,
                "hero_name": hero.template.name,
                "hero_rarity": hero.template.rarity.value,
                "old_level": old_level,
                "new_level": new_level,
                "gold_spent": gold_spent,
                "power_before": power_before,
                "power_after": power_after,
            },
        )

    def emit_hero_ascend(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        hero: HeroInstance,
        old_stars: int,
        new_stars: int,
        duplicates_used: int,
        power_before: int,
        power_after: int,
    ) -> Event:
        """Emit hero_ascend event."""
        return self._create_event(
            "hero_ascend",
            timestamp,
            agent,
            current_date,
            {
                "hero_id": hero.hero_id,
                "hero_name": hero.template.name,
                "hero_rarity": hero.template.rarity.value,
                "old_stars": old_stars,
                "new_stars": new_stars,
                "duplicates_used": duplicates_used,
                "power_before": power_before,
                "power_after": power_after,
            },
        )

    def emit_hero_team_change(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        old_team: list[str],
        new_team: list[str],
        team_power_before: int,
        team_power_after: int,
        change_reason: str,
    ) -> Event:
        """Emit hero_team_change event."""
        return self._create_event(
            "hero_team_change",
            timestamp,
            agent,
            current_date,
            {
                "old_team": old_team,
                "new_team": new_team,
                "team_power_before": team_power_before,
                "team_power_after": team_power_after,
                "change_reason": change_reason,
            },
        )

    # =========================================================================
    # SHOP EVENTS
    # =========================================================================

    def emit_shop_view(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        shop_tab: str,
        player_gems: int,
    ) -> Event:
        """Emit shop_view event."""
        return self._create_event(
            "shop_view",
            timestamp,
            agent,
            current_date,
            {
                "shop_tab": shop_tab,
                "player_gems": player_gems,
            },
        )

    def emit_iap_initiated(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        product_id: str,
        product_name: str,
        price_usd: float,
    ) -> Event:
        """Emit iap_initiated event."""
        return self._create_event(
            "iap_initiated",
            timestamp,
            agent,
            current_date,
            {
                "product_id": product_id,
                "product_name": product_name,
                "price_usd": price_usd,
            },
        )

    def emit_iap_purchase(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        product_id: str,
        product_name: str,
        price_usd: float,
        gems_received: int,
        items_received: list[dict],
        is_first_purchase: bool,
        purchase_number: int,
        vip_points_earned: int,
    ) -> Event:
        """Emit iap_purchase event."""
        return self._create_event(
            "iap_purchase",
            timestamp,
            agent,
            current_date,
            {
                "product_id": product_id,
                "product_name": product_name,
                "price_usd": price_usd,
                "gems_received": gems_received,
                "items_received": items_received,
                "is_first_purchase": is_first_purchase,
                "purchase_number": purchase_number,
                "transaction_id": generate_transaction_id(timestamp),
                "vip_points_earned": vip_points_earned,
            },
        )

    def emit_iap_failed(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        product_id: str,
        price_usd: float,
        fail_reason: str,
    ) -> Event:
        """Emit iap_failed event."""
        return self._create_event(
            "iap_failed",
            timestamp,
            agent,
            current_date,
            {
                "product_id": product_id,
                "price_usd": price_usd,
                "fail_reason": fail_reason,
            },
        )

    # =========================================================================
    # ADS EVENTS
    # =========================================================================

    def emit_ad_opportunity(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        placement: str,
        ads_watched_today: int,
        ads_available: int,
    ) -> Event:
        """Emit ad_opportunity event."""
        return self._create_event(
            "ad_opportunity",
            timestamp,
            agent,
            current_date,
            {
                "placement": placement,
                "ads_watched_today": ads_watched_today,
                "ads_available": ads_available,
            },
        )

    def emit_ad_started(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        placement: str,
        ad_network: str,
    ) -> Event:
        """Emit ad_started event."""
        return self._create_event(
            "ad_started",
            timestamp,
            agent,
            current_date,
            {
                "placement": placement,
                "ad_network": ad_network,
            },
        )

    def emit_ad_completed(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        placement: str,
        ad_network: str,
        reward_currency: str,
        reward_amount: int,
        watch_duration_sec: int,
    ) -> Event:
        """Emit ad_completed event."""
        return self._create_event(
            "ad_completed",
            timestamp,
            agent,
            current_date,
            {
                "placement": placement,
                "ad_network": ad_network,
                "reward_currency": reward_currency,
                "reward_amount": reward_amount,
                "watch_duration_sec": watch_duration_sec,
            },
        )

    def emit_ad_skipped(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        placement: str,
        ad_network: str,
        skip_after_sec: int,
        skip_reason: str,
    ) -> Event:
        """Emit ad_skipped event."""
        return self._create_event(
            "ad_skipped",
            timestamp,
            agent,
            current_date,
            {
                "placement": placement,
                "ad_network": ad_network,
                "skip_after_sec": skip_after_sec,
                "skip_reason": skip_reason,
            },
        )

    # =========================================================================
    # SOCIAL EVENTS
    # =========================================================================

    def emit_arena_battle_start(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        opponent_user_id: str,
        opponent_power: int,
        opponent_rank: int,
        player_power: int,
        player_rank: int,
        attempt_number: int,
        is_paid_attempt: bool,
    ) -> Event:
        """Emit arena_battle_start event."""
        return self._create_event(
            "arena_battle_start",
            timestamp,
            agent,
            current_date,
            {
                "opponent_user_id": opponent_user_id,
                "opponent_power": opponent_power,
                "opponent_rank": opponent_rank,
                "player_power": player_power,
                "player_rank": player_rank,
                "attempt_number": attempt_number,
                "is_paid_attempt": is_paid_attempt,
            },
        )

    def emit_arena_battle_end(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        opponent_user_id: str,
        result: str,
        duration_sec: int,
        rank_before: int,
        rank_after: int,
        rating_change: int,
        reward_currency: Optional[str] = None,
        reward_amount: Optional[int] = None,
    ) -> Event:
        """Emit arena_battle_end event."""
        props = {
            "opponent_user_id": opponent_user_id,
            "result": result,
            "duration_sec": duration_sec,
            "rank_before": rank_before,
            "rank_after": rank_after,
            "rating_change": rating_change,
        }
        if reward_currency:
            props["reward_currency"] = reward_currency
            props["reward_amount"] = reward_amount
        return self._create_event("arena_battle_end", timestamp, agent, current_date, props)

    def emit_guild_join(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        guild: Guild,
        join_method: str,
    ) -> Event:
        """Emit guild_join event."""
        return self._create_event(
            "guild_join",
            timestamp,
            agent,
            current_date,
            {
                "guild_id": guild.guild_id,
                "guild_name": guild.name,
                "guild_member_count": guild.member_count,
                "join_method": join_method,
            },
        )

    def emit_guild_leave(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        guild: Guild,
        reason: str,
        days_in_guild: int,
    ) -> Event:
        """Emit guild_leave event."""
        return self._create_event(
            "guild_leave",
            timestamp,
            agent,
            current_date,
            {
                "guild_id": guild.guild_id,
                "guild_name": guild.name,
                "reason": reason,
                "days_in_guild": days_in_guild,
            },
        )

    def emit_guild_boss_attack(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        guild_id: str,
        boss_id: str,
        boss_level: int,
        damage_dealt: int,
        team_power: int,
        attempt_number: int,
        boss_hp_remaining_pct: float,
    ) -> Event:
        """Emit guild_boss_attack event."""
        return self._create_event(
            "guild_boss_attack",
            timestamp,
            agent,
            current_date,
            {
                "guild_id": guild_id,
                "boss_id": boss_id,
                "boss_level": boss_level,
                "damage_dealt": damage_dealt,
                "team_power": team_power,
                "attempt_number": attempt_number,
                "boss_hp_remaining_pct": boss_hp_remaining_pct,
            },
        )

    # =========================================================================
    # QUEST EVENTS
    # =========================================================================

    def emit_quest_complete(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        quest_id: str,
        quest_type: str,
        quest_name: str,
        reward_currency: str,
        reward_amount: int,
        time_to_complete_sec: Optional[int] = None,
    ) -> Event:
        """Emit quest_complete event."""
        props = {
            "quest_id": quest_id,
            "quest_type": quest_type,
            "quest_name": quest_name,
            "reward_currency": reward_currency,
            "reward_amount": reward_amount,
        }
        if time_to_complete_sec is not None:
            props["time_to_complete_sec"] = time_to_complete_sec
        return self._create_event("quest_complete", timestamp, agent, current_date, props)

    def emit_daily_login(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        login_streak: int,
        reward_day: int,
        reward_currency: str,
        reward_amount: int,
        is_streak_bonus: bool,
    ) -> Event:
        """Emit daily_login event."""
        return self._create_event(
            "daily_login",
            timestamp,
            agent,
            current_date,
            {
                "login_streak": login_streak,
                "reward_day": reward_day,
                "reward_currency": reward_currency,
                "reward_amount": reward_amount,
                "is_streak_bonus": is_streak_bonus,
            },
        )

    # =========================================================================
    # EVENT EVENTS (Game Events/Temporary Activities)
    # =========================================================================

    def emit_event_start(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        game_event: GameEvent,
    ) -> Event:
        """Emit event_start event (player starts participating in game event)."""
        return self._create_event(
            "event_start",
            timestamp,
            agent,
            current_date,
            {
                "event_id": game_event.event_id,
                "event_type": game_event.event_type,
                "event_name": game_event.event_name,
                "event_start_date": game_event.start_date.isoformat(),
                "event_end_date": game_event.end_date.isoformat(),
                "days_remaining": game_event.days_remaining(current_date),
            },
        )

    def emit_event_progress(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        game_event: GameEvent,
        milestone_reached: int,
        milestone_target: int,
        progress_value: int,
        reward_claimed: bool,
        reward_currency: Optional[str] = None,
        reward_amount: Optional[int] = None,
    ) -> Event:
        """Emit event_progress event."""
        props = {
            "event_id": game_event.event_id,
            "event_type": game_event.event_type,
            "milestone_reached": milestone_reached,
            "milestone_target": milestone_target,
            "progress_value": progress_value,
            "reward_claimed": reward_claimed,
        }
        if reward_currency:
            props["reward_currency"] = reward_currency
            props["reward_amount"] = reward_amount
        return self._create_event("event_progress", timestamp, agent, current_date, props)

    def emit_event_complete(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        game_event: GameEvent,
        total_progress: int,
        milestones_completed: int,
        total_rewards_currency: str,
        total_rewards_amount: int,
    ) -> Event:
        """Emit event_complete event."""
        return self._create_event(
            "event_complete",
            timestamp,
            agent,
            current_date,
            {
                "event_id": game_event.event_id,
                "event_type": game_event.event_type,
                "total_progress": total_progress,
                "milestones_completed": milestones_completed,
                "total_rewards_currency": total_rewards_currency,
                "total_rewards_amount": total_rewards_amount,
            },
        )

    # =========================================================================
    # SYSTEM EVENTS
    # =========================================================================

    def emit_player_state_snapshot(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
    ) -> Event:
        """Emit player_state_snapshot event (daily snapshot)."""
        max_stage_id = f"ch{agent.max_chapter:02d}_st{agent.max_stage:02d}"
        return self._create_event(
            "player_state_snapshot",
            timestamp,
            agent,
            current_date,
            {
                "snapshot_date": current_date.isoformat(),
                "player_level": agent.player_level,
                "vip_level": agent.vip_level,
                "total_spent_usd": round(agent.total_spent_usd, 2),
                "gold_balance": agent.gold,
                "gems_balance": agent.gems,
                "energy_balance": agent.energy,
                "summon_tickets_balance": agent.summon_tickets,
                "heroes_count": len(agent.heroes),
                "heroes_by_rarity": agent.get_heroes_by_rarity(),
                "max_hero_level": agent.get_max_hero_level(),
                "max_hero_stars": agent.get_max_hero_stars(),
                "team_power": agent.team_power,
                "max_chapter": agent.max_chapter,
                "max_stage": agent.max_stage,
                "total_stages_cleared": agent.total_stages_cleared,
                "arena_rank": agent.arena_rank if agent.arena_rank > 0 else None,
                "arena_rating": agent.arena_rating if agent.arena_rank > 0 else None,
                "guild_id": agent.guild_id,
                "total_sessions": agent.total_sessions,
                "total_playtime_sec": agent.total_playtime_sec,
                "total_gacha_pulls": agent.total_gacha_pulls,
                "pity_counter": agent.pity_counter,
                "last_active_date": current_date.isoformat(),
            },
        )

    def emit_tutorial_step(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        step_id: str,
        step_number: int,
        step_name: str,
        duration_sec: int,
        is_skipped: bool,
    ) -> Event:
        """Emit tutorial_step event."""
        return self._create_event(
            "tutorial_step",
            timestamp,
            agent,
            current_date,
            {
                "step_id": step_id,
                "step_number": step_number,
                "step_name": step_name,
                "duration_sec": duration_sec,
                "is_skipped": is_skipped,
            },
        )

    def emit_tutorial_complete(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        total_duration_sec: int,
        steps_completed: int,
        steps_skipped: int,
    ) -> Event:
        """Emit tutorial_complete event."""
        return self._create_event(
            "tutorial_complete",
            timestamp,
            agent,
            current_date,
            {
                "total_duration_sec": total_duration_sec,
                "steps_completed": steps_completed,
                "steps_skipped": steps_skipped,
            },
        )

    def emit_error(
        self,
        agent: AgentState,
        timestamp: datetime,
        current_date: date,
        error_type: str,
        error_code: int,
        error_message: str,
        error_context: Optional[str] = None,
    ) -> Event:
        """Emit error event."""
        props = {
            "error_type": error_type,
            "error_code": error_code,
            "error_message": error_message,
        }
        if error_context:
            props["error_context"] = error_context
        return self._create_event("error", timestamp, agent, current_date, props)
