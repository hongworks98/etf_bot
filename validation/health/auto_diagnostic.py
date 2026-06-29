"""
validation/health/auto_diagnostic.py
Auto Diagnostic — 어떤 Engine이 성능 저하를 유발하는지 자동 진단
"""
from __future__ import annotations
from typing import Dict, List
from validation.data_models import (
    EngineHealthScore, DiagnosticFinding,
    DiagnosticResult, DiagnosticSeverity
)

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0

THRESHOLDS = {
    "accuracy":     (60.0, 45.0),   # (warning, critical)
    "consistency":  (55.0, 40.0),
    "calibration":  (60.0, 45.0),
    "overall":      (55.0, 40.0),
}

CAUSE_MAP = {
    "accuracy":    "신호 방향성 오류 — 매크로 체제 감지 실패 또는 노이즈 과다",
    "consistency": "신호 불안정 — 입력 데이터 변동성 과대 또는 파라미터 과민",
    "calibration": "신뢰도 보정 오류 — Confidence 과신 경향 또는 과소 신뢰",
    "overall":     "복합 성능 저하 — 다수 지표 동시 하락",
}

RECO_MAP = {
    "accuracy":    "학습 데이터 재검토 및 역 시장 국면 케이스 추가",
    "consistency": "신호 스무딩 필터 적용 또는 입력 정규화 강화",
    "calibration": "Confidence Calibration 재훈련 (Platt Scaling 등)",
    "overall":     "Engine 전체 하이퍼파라미터 재최적화 필요",
}


class AutoDiagnostic:
    """
    Scans EngineHealthScore results, identifies degraded engines,
    assigns root cause and recommendation.
    """

    def diagnose(
        self,
        health: Dict[str, EngineHealthScore],
    ) -> DiagnosticResult:
        findings: List[DiagnosticFinding] = []
        degraded, healthy = [], []

        for engine, h in health.items():
            for metric, (warn_th, crit_th) in THRESHOLDS.items():
                value = getattr(h, metric, 100.0)
                if value < crit_th:
                    sev = DiagnosticSeverity.CRITICAL
                elif value < warn_th:
                    sev = DiagnosticSeverity.WARNING
                else:
                    continue

                findings.append(DiagnosticFinding(
                    engine=engine,
                    severity=sev,
                    issue=f"{engine} {metric} = {value:.1f} (임계값 {warn_th:.0f})",
                    root_cause=CAUSE_MAP.get(metric, "원인 미상"),
                    recommendation=RECO_MAP.get(metric, "전문가 검토 필요"),
                ))

            if h.overall < THRESHOLDS["overall"][0]:
                if engine not in degraded:
                    degraded.append(engine)
            else:
                if engine not in healthy:
                    healthy.append(engine)

        overall_health = _mean([h.overall for h in health.values()]) if health else 0.0

        # Sort by severity (critical first)
        findings.sort(key=lambda f: 0 if f.severity == DiagnosticSeverity.CRITICAL else 1)

        crit_cnt = sum(1 for f in findings if f.severity == DiagnosticSeverity.CRITICAL)
        warn_cnt = len(findings) - crit_cnt
        xai = (f"전체 건강도: {overall_health:.1f} | "
               f"위험 {crit_cnt}건 / 경고 {warn_cnt}건 | "
               f"저하 Engine: {', '.join(degraded) or '없음'}")

        return DiagnosticResult(
            findings=findings,
            degraded_engines=degraded,
            healthy_engines=healthy,
            overall_health=round(overall_health, 1),
            xai_summary=xai,
        )
