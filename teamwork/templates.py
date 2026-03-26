"""
Pre-built team and service templates for quick setup.
"""
from __future__ import annotations

from .agent_config import AgentProfile, TeamConfig


# --- Team Templates ---

TEAM_TEMPLATES = {
    "solo": {
        "name": "Solo Agent",
        "description": "Single agent setup for individual developers",
        "config": TeamConfig(
            name="Solo Agent",
            description="Single agent operation",
            max_members=1,
            quality_threshold=7.0,
            auto_assign=True,
            routing_mode="round_robin",
        ),
        "agents": [
            AgentProfile(
                agent_id="__PLACEHOLDER__",
                role="leader",
                skills=("general",),
                max_concurrent_tasks=10,
            ),
        ],
        "quality_gates": [
            {"gate_type": "basic_check", "threshold": 7.0, "gate_order": 0},
        ],
    },
    "small_team": {
        "name": "Small Team",
        "description": "3-5 agents with keyword routing and quality review",
        "config": TeamConfig(
            name="Small Team",
            description="Collaborative team with routing and QA",
            max_members=5,
            quality_threshold=8.5,
            auto_assign=True,
            routing_mode="keyword",
        ),
        "agents": [
            AgentProfile(
                agent_id="__LEADER__",
                role="leader",
                skills=("management", "review"),
                max_concurrent_tasks=5,
                priority=10,
            ),
            AgentProfile(
                agent_id="__WORKER_1__",
                role="worker",
                skills=("coding", "debugging"),
                max_concurrent_tasks=5,
            ),
            AgentProfile(
                agent_id="__WORKER_2__",
                role="worker",
                skills=("writing", "research"),
                max_concurrent_tasks=5,
            ),
            AgentProfile(
                agent_id="__REVIEWER__",
                role="reviewer",
                skills=("qa", "testing"),
                max_concurrent_tasks=3,
            ),
        ],
        "quality_gates": [
            {"gate_type": "expert_review", "threshold": 8.0, "gate_order": 0},
            {"gate_type": "qa_score", "threshold": 8.5, "gate_order": 1},
        ],
        "routing_rules": [
            {"name": "Code Tasks", "keywords": ["code", "fix", "debug", "implement"], "target": "__WORKER_1__", "priority": 10},
            {"name": "Content Tasks", "keywords": ["write", "blog", "research", "translate"], "target": "__WORKER_2__", "priority": 10},
            {"name": "Review Tasks", "keywords": ["review", "qa", "test", "check"], "target": "__REVIEWER__", "priority": 5},
        ],
    },
    "enterprise": {
        "name": "Enterprise Team",
        "description": "Full team with skill-based routing, multi-gate QA, and specialized roles",
        "config": TeamConfig(
            name="Enterprise Team",
            description="Production-grade team with comprehensive quality pipeline",
            max_members=20,
            quality_threshold=9.0,
            auto_assign=True,
            routing_mode="skill_match",
        ),
        "agents": [
            AgentProfile(
                agent_id="__CTO__",
                role="leader",
                skills=("architecture", "management", "review"),
                max_concurrent_tasks=3,
                priority=20,
            ),
            AgentProfile(
                agent_id="__BACKEND__",
                role="worker",
                skills=("python", "api", "database", "backend"),
                max_concurrent_tasks=5,
            ),
            AgentProfile(
                agent_id="__FRONTEND__",
                role="worker",
                skills=("react", "css", "ui", "frontend"),
                max_concurrent_tasks=5,
            ),
            AgentProfile(
                agent_id="__DATA__",
                role="worker",
                skills=("data", "ml", "analysis", "pipeline"),
                max_concurrent_tasks=5,
            ),
            AgentProfile(
                agent_id="__QA__",
                role="reviewer",
                skills=("testing", "qa", "security", "review"),
                max_concurrent_tasks=5,
            ),
            AgentProfile(
                agent_id="__ROUTER__",
                role="router",
                skills=("routing", "triage"),
                max_concurrent_tasks=20,
            ),
        ],
        "quality_gates": [
            {"gate_type": "expert_review", "threshold": 8.5, "gate_order": 0},
            {"gate_type": "qa_score", "threshold": 9.0, "gate_order": 1},
            {"gate_type": "security_check", "threshold": 9.0, "gate_order": 2},
        ],
    },
}


# --- Service Templates ---

SERVICE_TEMPLATES = {
    "ai_api": {
        "name": "AI API Service",
        "description": "Machine learning inference API",
        "category": "ai",
        "tags": ["ai", "ml", "inference"],
        "price_per_call": "0.05",
        "free_tier_calls": 100,
        "payment_method": "x402",
    },
    "data_pipeline": {
        "name": "Data Pipeline Service",
        "description": "Data processing and ETL pipeline",
        "category": "data",
        "tags": ["data", "etl", "pipeline"],
        "price_per_call": "0.10",
        "free_tier_calls": 50,
        "payment_method": "x402",
    },
    "content_api": {
        "name": "Content Generation API",
        "description": "Text generation and content creation",
        "category": "content",
        "tags": ["content", "text", "generation"],
        "price_per_call": "0.02",
        "free_tier_calls": 200,
        "payment_method": "both",
    },
}


def get_team_template(template_name: str) -> dict | None:
    """Get a team template by name."""
    return TEAM_TEMPLATES.get(template_name)


def get_service_template(template_name: str) -> dict | None:
    """Get a service template by name."""
    return SERVICE_TEMPLATES.get(template_name)


def list_team_templates() -> list[dict]:
    """List available team templates."""
    return [
        {
            "id": k,
            "name": v["name"],
            "description": v["description"],
            "agent_count": len(v.get("agents", [])),
            "gate_count": len(v.get("quality_gates", [])),
        }
        for k, v in TEAM_TEMPLATES.items()
    ]


def list_service_templates() -> list[dict]:
    """List available service templates."""
    return [
        {
            "id": k,
            "name": v["name"],
            "description": v["description"],
            "category": v["category"],
            "price_per_call": v["price_per_call"],
        }
        for k, v in SERVICE_TEMPLATES.items()
    ]
