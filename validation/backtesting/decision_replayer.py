"""
validation/backtesting/decision_replayer.py
Decision Replay — 특정 날짜의 당시 의사결정 재현
"""
from __future__ import annotations
from typing import List, Optional
from validation.data_models import DecisionRecord, DecisionReplay


class DecisionReplayer:
    """Finds the decision record for a target date and formats it for replay."""

    ENGINE_FIELDS = {
        "Macro":     "macro_score",
        "Breadth":   "breadth_score",
        "RS":        "rs_score",
        "Rotation":  "rotation_score",
        "Portfolio": "portfolio_score",
        "Risk":      "risk_score",
    }

    def replay(
        self,
        records: List[DecisionRecord],
        target_date: str,
    ) -> Optional[DecisionReplay]:
        rec = next((r for r in records if r.date == target_date), None)
        if rec is None:
            # Nearest date fallback
            rec = min(records, key=lambda r: abs(r.date - target_date)
                      if isinstance(r.date, int) else 0) if records else None
        if rec is None:
            return None

        scores = {eng: round(getattr(rec, field, 50.0), 1)
                  for eng, field in self.ENGINE_FIELDS.items()}

        was_correct = rec.correct
        outcome = f"+{rec.actual_return*100:.2f}%" if rec.actual_return >= 0                   else f"{rec.actual_return*100:.2f}%"

        explanation = (
            f"날짜: {rec.date} | 결정: {rec.action} | "
            f"신뢰도: {rec.confidence:.1f} | "
            f"실제 결과: {outcome} | "
            f"{'✅ 정확' if was_correct else '❌ 오류'}"
        )

        return DecisionReplay(
            replay_date   = rec.date,
            engine_scores = scores,
            decision      = rec.action,
            confidence    = rec.confidence,
            weights       = rec.weights,
            actual_return = rec.actual_return,
            was_correct   = was_correct,
            explanation   = explanation,
        )
