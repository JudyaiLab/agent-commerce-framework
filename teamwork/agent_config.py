"""
Agent Configuration — define agent capabilities, roles, and constraints.
Productized version of openclaw.json agent definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AgentProfile:
    """Agent profile configuration within a team."""
    agent_id: str = ""
    role: str = "worker"  # leader | worker | reviewer | router
    skills: tuple[str, ...] = ()
    max_concurrent_tasks: int = 5
    timeout_seconds: int = 300
    retry_limit: int = 3
    priority: int = 0  # higher = more important
    constraints: dict = field(default_factory=dict)

    def matches_skill(self, required_skill: str) -> bool:
        """Check if agent has a required skill (case-insensitive)."""
        return required_skill.lower() in (s.lower() for s in self.skills)

    def matches_any_skill(self, required_skills: list[str]) -> bool:
        """Check if agent has any of the required skills."""
        return any(self.matches_skill(s) for s in required_skills)


@dataclass(frozen=True)
class TeamConfig:
    """Team-level configuration."""
    name: str = ""
    description: str = ""
    max_members: int = 20
    task_timeout_seconds: int = 600
    quality_threshold: float = 8.5
    auto_assign: bool = True
    routing_mode: str = "keyword"  # keyword | round_robin | skill_match
    metadata: dict = field(default_factory=dict)


def validate_agent_profile(profile: AgentProfile) -> list[str]:
    """Validate an agent profile. Returns list of errors (empty = valid)."""
    errors = []
    if not profile.agent_id:
        errors.append("agent_id is required")
    if profile.role not in ("leader", "worker", "reviewer", "router"):
        errors.append(f"Invalid role: {profile.role}")
    if profile.max_concurrent_tasks < 1:
        errors.append("max_concurrent_tasks must be >= 1")
    if profile.timeout_seconds < 1:
        errors.append("timeout_seconds must be >= 1")
    if profile.retry_limit < 0:
        errors.append("retry_limit must be >= 0")
    return errors


def validate_team_config(config: TeamConfig) -> list[str]:
    """Validate a team config. Returns list of errors (empty = valid)."""
    errors = []
    if not config.name:
        errors.append("Team name is required")
    if config.max_members < 1:
        errors.append("max_members must be >= 1")
    if config.quality_threshold < 0 or config.quality_threshold > 10:
        errors.append("quality_threshold must be between 0 and 10")
    if config.routing_mode not in ("keyword", "round_robin", "skill_match"):
        errors.append(f"Invalid routing_mode: {config.routing_mode}")
    return errors
