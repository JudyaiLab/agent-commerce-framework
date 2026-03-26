"""
Task Router — route tasks to the right agent based on keywords, skills, or round-robin.
Productized version of linear_dispatcher routing logic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .agent_config import AgentProfile


@dataclass(frozen=True)
class RoutingRule:
    """A rule that maps task patterns to target agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    keywords: tuple[str, ...] = ()
    target_agent_id: str = ""
    priority: int = 0
    enabled: bool = True


@dataclass(frozen=True)
class TaskAssignment:
    """Result of routing a task to an agent."""
    task_id: str = ""
    agent_id: str = ""
    rule_id: str = ""
    matched_keyword: str = ""
    routing_mode: str = ""
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TaskRouter:
    """Routes tasks to agents using configurable strategies."""

    def __init__(self, routing_mode: str = "keyword"):
        self.routing_mode = routing_mode
        self._round_robin_idx = 0

    def route(
        self,
        task_text: str,
        rules: list[dict],
        agents: list[AgentProfile],
        task_id: str = "",
    ) -> Optional[TaskAssignment]:
        """
        Route a task to an agent.

        Args:
            task_text: The task description to match against
            rules: List of routing rule dicts (from DB)
            agents: Available agent profiles
            task_id: Optional task identifier

        Returns:
            TaskAssignment if a match is found, None otherwise
        """
        if not task_id:
            task_id = str(uuid.uuid4())

        if self.routing_mode == "keyword":
            return self._route_by_keyword(task_text, rules, task_id)
        elif self.routing_mode == "skill_match":
            return self._route_by_skill(task_text, rules, agents, task_id)
        elif self.routing_mode == "round_robin":
            return self._route_round_robin(agents, task_id)
        return None

    def _route_by_keyword(
        self, task_text: str, rules: list[dict], task_id: str
    ) -> Optional[TaskAssignment]:
        """Match task text against keyword rules (highest priority first)."""
        text_lower = task_text.lower()
        sorted_rules = sorted(
            [r for r in rules if r.get("enabled", True)],
            key=lambda r: r.get("priority", 0),
            reverse=True,
        )

        for rule in sorted_rules:
            keywords = rule.get("keywords", [])
            for kw in keywords:
                if kw.lower() in text_lower:
                    return TaskAssignment(
                        task_id=task_id,
                        agent_id=rule["target_agent_id"],
                        rule_id=rule.get("id", ""),
                        matched_keyword=kw,
                        routing_mode="keyword",
                    )
        return None

    def _route_by_skill(
        self, task_text: str, rules: list[dict], agents: list[AgentProfile],
        task_id: str,
    ) -> Optional[TaskAssignment]:
        """Find agent with best skill match for the task."""
        text_lower = task_text.lower()

        # Extract required skills from task text by matching against agent skills
        best_agent = None
        best_score = 0

        for agent in agents:
            score = sum(1 for s in agent.skills if s.lower() in text_lower)
            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent:
            return TaskAssignment(
                task_id=task_id,
                agent_id=best_agent.agent_id,
                rule_id="",
                matched_keyword=f"skill_match(score={best_score})",
                routing_mode="skill_match",
            )
        return None

    def _route_round_robin(
        self, agents: list[AgentProfile], task_id: str
    ) -> Optional[TaskAssignment]:
        """Distribute tasks evenly across agents."""
        if not agents:
            return None

        agent = agents[self._round_robin_idx % len(agents)]
        self._round_robin_idx += 1

        return TaskAssignment(
            task_id=task_id,
            agent_id=agent.agent_id,
            rule_id="",
            matched_keyword="",
            routing_mode="round_robin",
        )
