"""
Task Orchestrator — manages task lifecycle within a team.
Coordinates agents, routing, and quality gates.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from marketplace.db import Database

from .agent_config import AgentProfile, TeamConfig
from .task_router import TaskRouter, TaskAssignment
from .quality_gates import QualityPipeline, PipelineResult


@dataclass(frozen=True)
class Task:
    """A task within the team system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str = ""
    title: str = ""
    description: str = ""
    status: str = "pending"  # pending | assigned | in_progress | review | completed | failed
    assigned_to: str = ""
    created_by: str = ""
    priority: int = 0
    result: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OrchestratorError(Exception):
    """Orchestration errors."""


class TeamOrchestrator:
    """
    Manages the lifecycle of tasks within a team.

    Flow:
    1. Task submitted → route to agent
    2. Agent works → submits result
    3. Result goes through quality gates
    4. If passed → mark completed
    5. If failed → retry or reassign
    """

    def __init__(self, db: Database, team_id: str):
        self.db = db
        self.team_id = team_id
        self._tasks: dict[str, Task] = {}
        self._retry_counts: dict[str, int] = {}

    def submit_task(
        self,
        title: str,
        description: str = "",
        created_by: str = "",
        priority: int = 0,
    ) -> Task:
        """Submit a new task for routing and assignment."""
        if not title or not title.strip():
            raise OrchestratorError("Task title is required")

        task = Task(
            id=str(uuid.uuid4()),
            team_id=self.team_id,
            title=title.strip(),
            description=description.strip(),
            status="pending",
            created_by=created_by,
            priority=priority,
        )
        self._tasks[task.id] = task
        return task

    def assign_task(
        self,
        task_id: str,
        agent_id: str,
        rule_id: str = "",
    ) -> Task:
        """Assign a task to an agent."""
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Task {task_id} not found")

        now = datetime.now(timezone.utc)
        updated = Task(
            id=task.id,
            team_id=task.team_id,
            title=task.title,
            description=task.description,
            status="assigned",
            assigned_to=agent_id,
            created_by=task.created_by,
            priority=task.priority,
            result=task.result,
            created_at=task.created_at,
            updated_at=now,
        )
        self._tasks[task_id] = updated
        return updated

    def route_and_assign(
        self,
        task_id: str,
        router: TaskRouter,
        rules: list[dict],
        agents: list[AgentProfile],
    ) -> Optional[TaskAssignment]:
        """Route a task and assign it to the matched agent."""
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Task {task_id} not found")

        assignment = router.route(
            task_text=f"{task.title} {task.description}",
            rules=rules,
            agents=agents,
            task_id=task_id,
        )

        if assignment:
            self.assign_task(task_id, assignment.agent_id, assignment.rule_id)

        return assignment

    def submit_result(
        self,
        task_id: str,
        result: dict,
        pipeline: Optional[QualityPipeline] = None,
    ) -> tuple[Task, Optional[PipelineResult]]:
        """
        Submit a task result, optionally running it through quality gates.

        Returns (updated_task, pipeline_result or None).
        """
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Task {task_id} not found")

        now = datetime.now(timezone.utc)
        pipeline_result = None

        if pipeline:
            pipeline_result = pipeline.evaluate(result)
            status = "completed" if pipeline_result.passed else "review"
        else:
            status = "completed"

        updated = Task(
            id=task.id,
            team_id=task.team_id,
            title=task.title,
            description=task.description,
            status=status,
            assigned_to=task.assigned_to,
            created_by=task.created_by,
            priority=task.priority,
            result=result,
            created_at=task.created_at,
            updated_at=now,
        )
        self._tasks[task_id] = updated

        return updated, pipeline_result

    def retry_task(
        self, task_id: str, max_retries: int = 3
    ) -> Optional[Task]:
        """Retry a failed/review task. Returns None if max retries exceeded."""
        task = self._tasks.get(task_id)
        if not task:
            raise OrchestratorError(f"Task {task_id} not found")

        count = self._retry_counts.get(task_id, 0)
        if count >= max_retries:
            # Three strikes — mark failed
            now = datetime.now(timezone.utc)
            failed = Task(
                id=task.id,
                team_id=task.team_id,
                title=task.title,
                description=task.description,
                status="failed",
                assigned_to=task.assigned_to,
                created_by=task.created_by,
                priority=task.priority,
                result=task.result,
                created_at=task.created_at,
                updated_at=now,
            )
            self._tasks[task_id] = failed
            return None

        self._retry_counts[task_id] = count + 1

        now = datetime.now(timezone.utc)
        retried = Task(
            id=task.id,
            team_id=task.team_id,
            title=task.title,
            description=task.description,
            status="assigned",
            assigned_to=task.assigned_to,
            created_by=task.created_by,
            priority=task.priority,
            result={},
            created_at=task.created_at,
            updated_at=now,
        )
        self._tasks[task_id] = retried
        return retried

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self, status: str | None = None, assigned_to: str | None = None
    ) -> list[Task]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def get_stats(self) -> dict:
        """Get task statistics."""
        tasks = list(self._tasks.values())
        by_status: dict[str, int] = {}
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1
        return {
            "total": len(tasks),
            "by_status": by_status,
            "retry_counts": dict(self._retry_counts),
        }
