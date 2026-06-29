"""
dss_integration/core/dss_result.py
DSSResult — 모든 Engine 결과를 하나로 통합하는 최상위 결과 객체.
향후 Streamlit은 이 객체 하나만 사용한다.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional
from dss_integration.monitor.monitor_models import DSSMonitorResult


@dataclass
class DSSResult:
    """
    전체 DSS 파이프라인 실행 결과.
    JSON 직렬화 가능하도록 모든 필드는 기본 타입 또는 dataclass.
    """
    # ── Engine Results ────────────────────────────────────────────────
    macro_result:                  Any = None
    breadth_result:                Any = None
    rs_result:                     Any = None
    rotation_result:               Any = None
    portfolio_decision_result:     Any = None
    portfolio_optimization_result: Any = None
    validation_result:             Any = None
    dashboard_result:              Any = None

    # ── Meta ─────────────────────────────────────────────────────────
    monitor_result:    Optional[DSSMonitorResult] = None
    run_date:          str = ""
    run_id:            str = ""
    pipeline_success:  bool = True
    pipeline_error:    Optional[str] = None

    # ── Derived Properties ────────────────────────────────────────────

    @property
    def overall_confidence(self) -> float:
        """Dashboard 신뢰도 (없으면 0)."""
        d = self.dashboard_result
        return getattr(d, "confidence", 0.0) if d else 0.0

    @property
    def recommended_action(self) -> str:
        """최종 권고 액션."""
        td = getattr(self.dashboard_result, "today_decision", None) if self.dashboard_result else None
        action = getattr(getattr(td, "primary_action", None), "value", None) if td else None
        if action:
            return action
        # Fallback: portfolio decision
        pd = self.portfolio_decision_result
        return getattr(pd, "action", "WAIT") if pd else "WAIT"

    @property
    def top_opportunities(self) -> List[str]:
        """상위 기회 ETF 목록."""
        rot = self.rotation_result
        if rot:
            dominant = getattr(rot, "dominant_rotation", None)
            return [dominant] if dominant else []
        return []

    @property
    def system_health(self) -> str:
        """시스템 전체 건강 상태."""
        if not self.monitor_result:
            return "UNKNOWN"
        if self.monitor_result.all_success:
            return "HEALTHY"
        if len(self.monitor_result.failed_engines) >= 3:
            return "CRITICAL"
        return "DEGRADED"

    @property
    def macro_state(self) -> str:
        m = self.macro_result
        return getattr(m, "macro_state", "Unknown") if m else "Unknown"

    @property
    def validation_grade(self) -> str:
        v = self.validation_result
        if not v:
            return "N/A"
        g = getattr(v, "overall_grade", None)
        return g.value if g else "N/A"
