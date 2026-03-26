"""
Quality Gates — configurable pipeline for validating task outputs.
Inspired by GATE-5/6 patterns from the operating system.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class GateResult:
    """Result of passing through a single quality gate."""
    gate_type: str
    passed: bool
    score: float = 0.0
    reason: str = ""
    gate_order: int = 0


@dataclass(frozen=True)
class PipelineResult:
    """Result of running the full quality pipeline."""
    passed: bool
    overall_score: float = 0.0
    gate_results: tuple[GateResult, ...] = ()
    failed_gate: Optional[str] = None


class QualityGate:
    """A single quality gate that evaluates task output."""

    def __init__(
        self,
        gate_type: str,
        threshold: float,
        gate_order: int = 0,
        config: dict | None = None,
    ):
        self.gate_type = gate_type
        self.threshold = threshold
        self.gate_order = gate_order
        self.config = config or {}

    def evaluate(self, output: dict) -> GateResult:
        """
        Evaluate output against this gate.

        Output dict should contain:
        - score: float (0-10)
        - content: str (the actual output)
        - metadata: dict (extra info)
        """
        score = output.get("score", 0.0)
        passed = score >= self.threshold

        reason = ""
        if not passed:
            reason = (
                f"{self.gate_type}: score {score:.1f} < threshold {self.threshold:.1f}"
            )

        return GateResult(
            gate_type=self.gate_type,
            passed=passed,
            score=score,
            reason=reason,
            gate_order=self.gate_order,
        )


class QualityPipeline:
    """
    Pipeline of quality gates that output must pass through.
    Gates are evaluated in order. Pipeline stops on first failure.
    """

    def __init__(self, gates: list[QualityGate] | None = None):
        self.gates = sorted(gates or [], key=lambda g: g.gate_order)

    def add_gate(self, gate: QualityGate) -> None:
        """Add a gate to the pipeline (maintains sort order)."""
        gates = list(self.gates) + [gate]
        self.gates = sorted(gates, key=lambda g: g.gate_order)

    def evaluate(self, output: dict) -> PipelineResult:
        """
        Run output through all gates in order.
        Stops on first failure.
        """
        if not self.gates:
            return PipelineResult(passed=True, overall_score=10.0)

        results = []
        for gate in self.gates:
            result = gate.evaluate(output)
            results.append(result)
            if not result.passed:
                return PipelineResult(
                    passed=False,
                    overall_score=result.score,
                    gate_results=tuple(results),
                    failed_gate=gate.gate_type,
                )

        # All passed — average score
        avg_score = sum(r.score for r in results) / len(results)
        return PipelineResult(
            passed=True,
            overall_score=round(avg_score, 2),
            gate_results=tuple(results),
        )

    @classmethod
    def from_db_records(cls, records: list[dict]) -> "QualityPipeline":
        """Create pipeline from database records."""
        gates = [
            QualityGate(
                gate_type=r["gate_type"],
                threshold=r["threshold"],
                gate_order=r.get("gate_order", 0),
                config=r.get("config", {}),
            )
            for r in records
            if r.get("enabled", True)
        ]
        return cls(gates)
