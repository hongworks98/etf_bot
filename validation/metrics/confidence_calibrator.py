"""
validation/metrics/confidence_calibrator.py
Expected Calibration Error + Brier Score 계산
"""
from __future__ import annotations
import math
from typing import List
from validation.data_models import DecisionRecord, CalibrationResult, CalibrationBin

N_BINS = 10

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0

class ConfidenceCalibrator:
    """
    Maps confidence → actual win rate across bins.
    Computes ECE = Σ |accuracy_b - confidence_b| × |b|/N
    Brier = mean((confidence/100 - outcome)²)
    """

    def calibrate(self, records: List[DecisionRecord]) -> CalibrationResult:
        if not records:
            return self._empty()

        bins: List[List[DecisionRecord]] = [[] for _ in range(N_BINS)]
        for r in records:
            idx = min(int(r.confidence / 100 * N_BINS), N_BINS - 1)
            bins[idx].append(r)

        cal_bins = []
        for i, b in enumerate(bins):
            if not b:
                continue
            lo = i / N_BINS * 100
            hi = (i+1) / N_BINS * 100
            avg_conf = _mean([r.confidence for r in b])
            accuracy = sum(1 for r in b if r.correct) / len(b) * 100
            cal_bins.append(CalibrationBin(
                confidence_lo=round(lo,1),
                confidence_hi=round(hi,1),
                avg_confidence=round(avg_conf,2),
                actual_accuracy=round(accuracy,2),
                count=len(b),
            ))

        n = len(records)
        ece = sum(abs(b.actual_accuracy/100 - b.avg_confidence/100) * b.count / n
                  for b in cal_bins) * 100

        brier = _mean([(r.confidence/100 - (1.0 if r.correct else 0.0))**2
                       for r in records])

        overcnt = sum(1 for b in cal_bins if b.avg_confidence > b.actual_accuracy)
        undercnt = len(cal_bins) - overcnt

        xai = (f"ECE {ece:.1f}% | Brier {brier:.3f} | "
               f"과신 구간 {overcnt}개 / 과소신 {undercnt}개")

        return CalibrationResult(
            bins=cal_bins,
            ece=round(ece, 3),
            brier_score=round(brier, 4),
            overconfident_pct=round(overcnt/max(len(cal_bins),1)*100, 1),
            underconfident_pct=round(undercnt/max(len(cal_bins),1)*100, 1),
            xai_summary=xai,
        )

    @staticmethod
    def _empty() -> CalibrationResult:
        return CalibrationResult(
            bins=[], ece=0.0, brier_score=0.0,
            overconfident_pct=0.0, underconfident_pct=0.0,
            xai_summary="데이터 없음",
        )
