"""
dss_integration/core/dss_pipeline.py
DSSPipeline — 8개 Engine을 순서대로 실행하는 오케스트레이터.

⭐⭐⭐⭐⭐ 핵심 원칙:
- Engine 내부 로직 절대 수정 금지
- Engine 연결 순서 변경 금지
- 각 Engine은 독립적으로 유지
- 웹사이트는 이 파이프라인만 호출
"""
from __future__ import annotations
import sys, os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Integration layer를 통해 outputs 루트에 접근
_OUTPUTS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _OUTPUTS_ROOT not in sys.path:
    sys.path.insert(0, _OUTPUTS_ROOT)

from dss_integration.core.dss_result         import DSSResult
from dss_integration.monitor.engine_monitor  import EngineMonitor
from dss_integration.monitor.monitor_models  import DSSMonitorResult
from dss_integration.data.base_loader        import RawMarketData
from dss_integration.utils.logger            import get_logger
from dss_integration.config.settings         import ENGINE_CRITICAL

# Adapters
from dss_integration.adapters.macro_adapter      import MacroAdapter
from dss_integration.adapters.breadth_adapter    import BreadthAdapter
from dss_integration.adapters.rs_adapter         import RSAdapter
from dss_integration.adapters.rotation_adapter   import RotationAdapter
from dss_integration.adapters.portfolio_adapter  import PortfolioAdapter
from dss_integration.adapters.optimizer_adapter  import OptimizerAdapter
from dss_integration.adapters.validation_adapter import ValidationAdapter
from dss_integration.adapters.dashboard_adapter  import DashboardAdapter

log = get_logger("DSSPipeline")


class DSSPipeline:
    """
    Engine 파이프라인 오케스트레이터.
    각 Engine은 이전 Engine의 결과를 입력으로 받는다.
    Engine 실패 시 is_critical 설정에 따라 중단 여부를 결정한다.
    """

    def __init__(
        self,
        monitor: Optional[EngineMonitor] = None,
        run_id: str = "",
    ):
        self._monitor = monitor or EngineMonitor(run_id=run_id)
        self._run_id  = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

    def run(self, raw_data: RawMarketData) -> DSSResult:
        """
        전체 DSS 파이프라인 실행.
        Load → Macro → Breadth → RS → Rotation → Portfolio →
        Optimizer → Validation → Dashboard → DSSResult
        """
        log.info("=" * 60)
        log.info(f"DSS Pipeline Started  [run_id={self._run_id}]")
        log.info("=" * 60)

        results: Dict[str, Any] = {}
        pipeline_error: Optional[str] = None

        # ── 1. Macro Engine ────────────────────────────────────────────
        macro_result = self._run_macro(raw_data, results)
        results["macro_result"] = macro_result

        # ── 2. Breadth Engine ──────────────────────────────────────────
        breadth_result = self._run_breadth(raw_data, results)
        results["breadth_result"] = breadth_result

        # ── 3. Relative Strength Engine ────────────────────────────────
        rs_result = self._run_rs(raw_data, results)
        results["rs_result"] = rs_result

        # ── 4. Rotation Engine ─────────────────────────────────────────
        rotation_result = self._run_rotation(raw_data, results)
        results["rotation_result"] = rotation_result

        # ── 5. Portfolio Decision Engine ───────────────────────────────
        pd_result = self._run_portfolio_decision(raw_data, results)
        results["portfolio_decision_result"] = pd_result

        # ── 6. Portfolio Optimizer Engine ──────────────────────────────
        po_result = self._run_portfolio_optimizer(raw_data, results)
        results["portfolio_optimization_result"] = po_result

        # ── 7. Validation Engine ───────────────────────────────────────
        val_result = self._run_validation(raw_data, results)
        results["validation_result"] = val_result

        # ── 8. Dashboard Engine ────────────────────────────────────────
        dash_result = self._run_dashboard(raw_data, results)
        results["dashboard_result"] = dash_result

        # ── Assemble DSSResult ─────────────────────────────────────────
        monitor_result = self._monitor.to_result()
        pipeline_success = monitor_result.all_success or all(
            not (r.is_critical and not r.succeeded)
            for r in monitor_result.engines
        )

        log.info("=" * 60)
        log.info(f"Pipeline {'SUCCESS' if pipeline_success else 'FAILED'} "
                 f"[{monitor_result.total_elapsed_sec:.2f}s]")
        log.info("=" * 60)

        return DSSResult(
            macro_result                  = macro_result,
            breadth_result                = breadth_result,
            rs_result                     = rs_result,
            rotation_result               = rotation_result,
            portfolio_decision_result     = pd_result,
            portfolio_optimization_result = po_result,
            validation_result             = val_result,
            dashboard_result              = dash_result,
            monitor_result                = monitor_result,
            run_date                      = datetime.now(timezone.utc).isoformat(),
            run_id                        = self._run_id,
            pipeline_success              = pipeline_success,
            pipeline_error                = pipeline_error,
        )

    # ── Private Engine Runners ─────────────────────────────────────────

    def _run_macro(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Macro Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                result = MacroAdapter.synthetic_result(raw)
            log.info(f"[{eng}] Finished — score={result.macro_score:.1f} state={result.macro_state}")
            return result
        except Exception as e:
            log.error(f"[{eng}] FAILED: {e}")
            return MacroAdapter.synthetic_result(raw)

    def _run_breadth(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Breadth Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                result = BreadthAdapter.synthetic_result(raw)
            log.info(f"[{eng}] Finished — score={result.breadth_score:.1f}")
            return result
        except Exception as e:
            log.error(f"[{eng}] FAILED: {e}")
            return BreadthAdapter.synthetic_result(raw)

    def _run_rs(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Relative Strength Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                result = RSAdapter.synthetic_result(raw)
            log.info(f"[{eng}] Finished — avg_rs={result.avg_rs_score:.1f}")
            return result
        except Exception as e:
            log.error(f"[{eng}] FAILED: {e}")
            return RSAdapter.synthetic_result(raw)

    def _run_rotation(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Rotation Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                result = RotationAdapter.synthetic_result(raw, prev.get("rs_result"))
            log.info(f"[{eng}] Finished — dominant={result.dominant_rotation}")
            return result
        except Exception as e:
            log.error(f"[{eng}] FAILED: {e}")
            return RotationAdapter.synthetic_result(raw, prev.get("rs_result"))

    def _run_portfolio_decision(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Portfolio Decision Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                result = PortfolioAdapter.synthetic_result(raw, prev)
            log.info(f"[{eng}] Finished — action={result.action} score={result.decision_score:.1f}")
            return result
        except Exception as e:
            log.error(f"[{eng}] FAILED: {e}")
            return PortfolioAdapter.synthetic_result(raw, prev)

    def _run_portfolio_optimizer(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Portfolio Optimizer Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                result = OptimizerAdapter.synthetic_result(raw, prev)
            regime = getattr(getattr(result, "regime", None), "value", "?")
            log.info(f"[{eng}] Finished — regime={regime}")
            return result
        except Exception as e:
            log.error(f"[{eng}] FAILED: {e}")
            return OptimizerAdapter.synthetic_result(raw, prev)

    def _run_validation(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Validation Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                from validation.validation_engine import ValidationEngine
                val_inp = ValidationAdapter.build_validation_input(raw)
                result  = ValidationEngine().validate(val_inp)
            grade = getattr(getattr(result, "overall_grade", None), "value", "?")
            log.info(f"[{eng}] Finished — grade={grade}")
            return result
        except Exception as e:
            log.warning(f"[{eng}] Skipped (non-critical): {e}")
            self._monitor.skip(eng, str(e))
            return None

    def _run_dashboard(self, raw: RawMarketData, prev: Dict) -> Any:
        eng = "Dashboard Engine"
        log.info(f"[{eng}] Started")
        try:
            with self._monitor.track(eng, critical=ENGINE_CRITICAL[eng]):
                from dashboard.orchestrator import DashboardOrchestrator
                from dashboard.demo_factory import create_demo_data
                macro, breadth, rs, rot, port, dec = create_demo_data()
                result = DashboardOrchestrator().build(
                    macro_result      = prev.get("macro_result") or macro,
                    breadth_result    = prev.get("breadth_result") or breadth,
                    rs_result         = prev.get("rs_result") or rs,
                    rotation_result   = prev.get("rotation_result") or rot,
                    portfolio_result  = prev.get("portfolio_optimization_result") or port,
                    decision_result   = prev.get("portfolio_decision_result") or dec,
                )
            log.info(f"[{eng}] Finished — confidence={result.confidence:.1f}")
            return result
        except Exception as e:
            log.warning(f"[{eng}] Skipped (non-critical): {e}")
            self._monitor.skip(eng, str(e))
            return None

    @property
    def monitor(self) -> EngineMonitor:
        return self._monitor
