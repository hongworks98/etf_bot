"""
validation/analysis/explainability_auditor.py
XAI Consistency Audit — 결정의 일관성 점수
"""
from __future__ import annotations
from typing import List
from validation.data_models import (
    DecisionRecord, XAIConsistencyRecord, XAIAuditResult
)

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0


class ExplainabilityAuditor:
    """
    For each decision, checks how well the engine signals agree
    with the final decision. Inconsistency = signals pulling in opposite
    directions to the chosen action.
    """

    BUY_THRESHOLD  = 60.0
    SELL_THRESHOLD = 40.0

    def audit(self, records: List[DecisionRecord]) -> XAIAuditResult:
        if not records:
            return XAIAuditResult(
                records=[], avg_consistency=0.0,
                low_consistency_cnt=0, high_confidence_wrong=0,
                xai_summary="데이터 없음",
            )

        audit_records: List[XAIConsistencyRecord] = []

        for r in records:
            scores = {
                "Macro":     r.macro_score,
                "Breadth":   r.breadth_score,
                "RS":        r.rs_score,
                "Rotation":  r.rotation_score,
                "Portfolio": r.portfolio_score,
            }

            # Determine expected direction from action
            is_buy  = r.action in ("BUY",)
            is_sell = r.action in ("SELL",)

            contradictions = []
            agreeing = 0
            for eng, score in scores.items():
                if is_buy and score < self.SELL_THRESHOLD:
                    contradictions.append(f"{eng}({score:.0f}↓ vs BUY)")
                elif is_sell and score > self.BUY_THRESHOLD:
                    contradictions.append(f"{eng}({score:.0f}↑ vs SELL)")
                else:
                    agreeing += 1

            consistency = agreeing / len(scores) * 100

            audit_records.append(XAIConsistencyRecord(
                date=r.date,
                decision=r.action,
                confidence=r.confidence,
                feature_scores=scores,
                consistency_score=round(consistency, 1),
                contradictions=contradictions,
            ))

        avg_cons = _mean([a.consistency_score for a in audit_records])
        low_cnt  = sum(1 for a in audit_records if a.consistency_score < 50)
        hc_wrong = sum(1 for r, a in zip(records, audit_records)
                       if r.confidence > 70 and not r.correct)

        xai = (f"평균 일관성: {avg_cons:.1f}% | "
               f"저일관성 결정: {low_cnt}건 | "
               f"과신 오류: {hc_wrong}건")

        return XAIAuditResult(
            records=audit_records,
            avg_consistency=round(avg_cons, 2),
            low_consistency_cnt=low_cnt,
            high_confidence_wrong=hc_wrong,
            xai_summary=xai,
        )
