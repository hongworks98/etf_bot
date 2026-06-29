"""
validation/analysis/failure_analyzer.py
실패 패턴 분석 — 연속 손실, 큰 손실, 환경별 실패
"""
from __future__ import annotations
from collections import Counter
from typing import List, Optional
from validation.data_models import (
    DecisionRecord, FailureRecord, FailureAnalysisResult, FailureType
)

LOSS_THRESHOLD    = -0.02   # 2% single-day loss → failure
CONSECUTIVE_LIMIT =  3      # 3 consecutive losses → pattern


class FailureAnalyzer:
    def analyze(self, records: List[DecisionRecord]) -> FailureAnalysisResult:
        if not records:
            return self._empty()

        failures: List[FailureRecord] = []
        consecutive = 0

        for i, r in enumerate(records):
            ftype = None
            if r.actual_return < LOSS_THRESHOLD:
                ftype = FailureType.LARGE_DRAWDOWN
            elif not r.correct:
                ftype = FailureType.SIGNAL_MISS
                consecutive += 1
                if consecutive >= CONSECUTIVE_LIMIT:
                    ftype = FailureType.CONSECUTIVE_LOSS
            else:
                consecutive = 0

            # Confidence calibration miss
            if r.confidence > 70 and not r.correct:
                ftype = FailureType.CALIBRATION_MISS

            if ftype:
                context = self._context(r)
                failures.append(FailureRecord(
                    date=r.date, failure_type=ftype,
                    loss=round(r.actual_return, 6),
                    context=context,
                    engine_signals={
                        "macro": r.macro_score,
                        "breadth": r.breadth_score,
                        "rs": r.rs_score,
                    },
                ))

        by_type = Counter(f.failure_type.value for f in failures)
        worst   = min(failures, key=lambda f: f.loss) if failures else None

        ctx_count = Counter(f.context for f in failures)
        common_ctx = ctx_count.most_common(1)[0][0] if ctx_count else "N/A"

        # Recovery: average # records between failures
        fail_idx = [i for i,r in enumerate(records) if not r.correct]
        if len(fail_idx) >= 2:
            gaps = [fail_idx[i+1]-fail_idx[i] for i in range(len(fail_idx)-1)]
            recovery = sum(gaps)/len(gaps)
        else:
            recovery = float(len(records))

        fail_rate = len(failures) / max(len(records), 1)
        xai = (f"총 실패 {len(failures)}건 | 실패율 {fail_rate*100:.1f}% | "
               f"가장 흔한 환경: {common_ctx} | "
               f"평균 회복: {recovery:.1f}일")

        return FailureAnalysisResult(
            total_failures=len(failures),
            by_type=dict(by_type),
            worst_failure=worst,
            common_context=common_ctx,
            failure_rate=round(fail_rate, 4),
            recovery_avg_days=round(recovery, 1),
            xai_summary=xai,
        )

    @staticmethod
    def _context(r: DecisionRecord) -> str:
        if r.macro_score < 40:
            return "Recession/Slowdown"
        if r.macro_score > 70:
            return "Expansion"
        return "Neutral"

    @staticmethod
    def _empty() -> FailureAnalysisResult:
        return FailureAnalysisResult(
            total_failures=0, by_type={}, worst_failure=None,
            common_context="N/A", failure_rate=0.0,
            recovery_avg_days=0.0, xai_summary="데이터 없음",
        )
