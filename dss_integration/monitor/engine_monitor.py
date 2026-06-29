"""
dss_integration/monitor/engine_monitor.py
★★★★★ Engine Monitor — 실시간 Engine 상태 모니터링

사용법:
    monitor = EngineMonitor()

    with monitor.track("Macro Engine"):
        result = macro_engine.run(inp)

    monitor.print_report()
    dss_monitor = monitor.to_result()
"""
from __future__ import annotations

import time
import traceback
import tracemalloc
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, List, Optional

from dss_integration.monitor.monitor_models import (
    EngineStatus, EngineMonitorResult, DSSMonitorResult
)

# Optional: psutil for CPU/memory
try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class EngineMonitor:
    """
    Context-manager 기반 Engine 실행 모니터.
    각 Engine을 with monitor.track("이름") 으로 감싸면
    시간·메모리·오류를 자동으로 기록한다.
    """

    WIDTH = 55  # 출력 열 너비

    def __init__(self, run_id: str = ""):
        self._results: List[EngineMonitorResult] = []
        self._run_id  = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._pipeline_start = time.perf_counter()

    # ── Public API ─────────────────────────────────────────────────────

    @contextmanager
    def track(
        self,
        engine_name: str,
        critical: bool = True,
    ) -> Generator[None, None, None]:
        """
        with monitor.track("Macro Engine"):
            result = engine.run(...)
        """
        start_wall = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        mem_before = self._mem_mb()

        try:
            yield
            elapsed_ms = (time.perf_counter() - t0) * 1000
            mem_after  = self._mem_mb()
            mem_used   = (mem_after - mem_before) if (mem_before and mem_after) else None
            cpu        = self._cpu_pct()
            end_wall   = datetime.now(timezone.utc).isoformat()

            self._results.append(EngineMonitorResult(
                engine_name   = engine_name,
                status        = EngineStatus.SUCCESS,
                start_time    = start_wall,
                end_time      = end_wall,
                elapsed_ms    = elapsed_ms,
                memory_mb     = round(mem_used, 2) if mem_used else None,
                cpu_pct       = cpu,
                error_message = None,
                stack_trace   = None,
                is_critical   = critical,
            ))

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            end_wall   = datetime.now(timezone.utc).isoformat()
            tb_str     = traceback.format_exc()

            self._results.append(EngineMonitorResult(
                engine_name   = engine_name,
                status        = EngineStatus.FAILED,
                start_time    = start_wall,
                end_time      = end_wall,
                elapsed_ms    = elapsed_ms,
                memory_mb     = None,
                cpu_pct       = None,
                error_message = str(exc),
                stack_trace   = tb_str,
                is_critical   = critical,
            ))
            raise   # 호출자가 핸들링

    def skip(self, engine_name: str, reason: str = "") -> None:
        """명시적 skip 기록."""
        now = datetime.now(timezone.utc).isoformat()
        self._results.append(EngineMonitorResult(
            engine_name   = engine_name,
            status        = EngineStatus.SKIPPED,
            start_time    = now,
            end_time      = now,
            elapsed_ms    = 0.0,
            error_message = reason or "skipped",
            is_critical   = False,
        ))

    def print_report(self) -> None:
        """콘솔에 Engine Status 보고서 출력."""
        W = self.WIDTH
        total_ms = (time.perf_counter() - self._pipeline_start) * 1000

        print()
        print("┌" + "─" * W + "┐")
        print("│" + "  Engine Status".center(W) + "│")
        print("├" + "─" * W + "┤")

        for r in self._results:
            if r.succeeded:
                icon  = "✅"
                label = f"{r.engine_name}"
                right = f"{r.elapsed_sec:.2f}초"
            elif r.status == EngineStatus.SKIPPED:
                icon  = "⏭️ "
                label = f"{r.engine_name}"
                right = "SKIPPED"
            else:
                icon  = "❌"
                label = f"{r.engine_name}"
                right = f"{r.elapsed_sec:.2f}초  FAILED"

            # Dots padding
            avail  = W - 4 - len(label) - len(right)
            dots   = "." * max(3, avail)
            line   = f"  {icon} {label} {dots} {right}"
            print("│" + line.ljust(W) + "│")

            if not r.succeeded and r.status != EngineStatus.SKIPPED:
                err_line = f"     Error: {(r.error_message or '')[:W-12]}"
                print("│" + err_line.ljust(W) + "│")

        print("├" + "─" * W + "┤")
        total_sec = total_ms / 1000
        total_line = f"  Total Execution Time"
        right_t    = f"{total_sec:.2f}초"
        avail_t    = W - 4 - len(total_line) - len(right_t)
        dots_t     = "." * max(3, avail_t)
        print("│" + f"  {total_line} {dots_t} {right_t}".ljust(W) + "│")
        print("└" + "─" * W + "┘")

        # Failure details
        failed = [r for r in self._results if r.status == EngineStatus.FAILED]
        if failed:
            print()
            for r in failed:
                print(f"{'='*W}")
                print(f"❌ {r.engine_name} 실패 상세")
                print(f"  실행 시간 : {r.elapsed_sec:.3f}초")
                print(f"  오류      : {r.error_message}")
                if r.stack_trace:
                    print("  Stack Trace:")
                    for line in (r.stack_trace or "").splitlines()[-6:]:
                        print(f"    {line}")
                print(f"{'='*W}")
        print()

    def to_result(self) -> DSSMonitorResult:
        """DSSMonitorResult 객체로 변환 (JSON 직렬화 가능)."""
        total_ms = (time.perf_counter() - self._pipeline_start) * 1000
        failed   = [r.engine_name for r in self._results
                    if r.status == EngineStatus.FAILED]
        return DSSMonitorResult(
            engines          = self._results,
            total_elapsed_ms = round(total_ms, 2),
            all_success      = len(failed) == 0,
            failed_engines   = failed,
            run_id           = self._run_id,
        )

    @property
    def results(self) -> List[EngineMonitorResult]:
        return list(self._results)

    # ── Private ────────────────────────────────────────────────────────

    @staticmethod
    def _mem_mb() -> Optional[float]:
        if _HAS_PSUTIL:
            try:
                import os
                p = _psutil.Process(os.getpid())
                return p.memory_info().rss / 1024 / 1024
            except Exception:
                return None
        # tracemalloc fallback
        try:
            current, _ = tracemalloc.get_traced_memory()
            return current / 1024 / 1024
        except Exception:
            return None

    @staticmethod
    def _cpu_pct() -> Optional[float]:
        if _HAS_PSUTIL:
            try:
                import os
                p = _psutil.Process(os.getpid())
                return p.cpu_percent(interval=None)
            except Exception:
                return None
        return None
