"""
dss_integration/monitor/monitor_models.py
Engine Monitor 데이터 모델
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EngineStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED  = "FAILED"
    SKIPPED = "SKIPPED"
    RUNNING = "RUNNING"


@dataclass
class EngineMonitorResult:
    """단일 Engine 실행 결과 기록"""
    engine_name:   str
    status:        EngineStatus
    start_time:    str              # ISO 8601
    end_time:      str
    elapsed_ms:    float
    memory_mb:     Optional[float] = None
    cpu_pct:       Optional[float] = None
    error_message: Optional[str]   = None
    stack_trace:   Optional[str]   = None
    is_critical:   bool            = True  # 실패 시 파이프라인 중단 여부

    @property
    def elapsed_sec(self) -> float:
        return round(self.elapsed_ms / 1000, 3)

    @property
    def succeeded(self) -> bool:
        return self.status == EngineStatus.SUCCESS

    def to_dict(self) -> dict:
        return {
            "engine_name":   self.engine_name,
            "status":        self.status.value,
            "start_time":    self.start_time,
            "end_time":      self.end_time,
            "elapsed_ms":    round(self.elapsed_ms, 2),
            "elapsed_sec":   self.elapsed_sec,
            "memory_mb":     self.memory_mb,
            "cpu_pct":       self.cpu_pct,
            "error_message": self.error_message,
            "is_critical":   self.is_critical,
        }


@dataclass
class DSSMonitorResult:
    """전체 Pipeline 실행 결과 요약"""
    engines:          List[EngineMonitorResult] = field(default_factory=list)
    total_elapsed_ms: float = 0.0
    all_success:      bool  = True
    failed_engines:   List[str] = field(default_factory=list)
    run_id:           str   = ""

    @property
    def total_elapsed_sec(self) -> float:
        return round(self.total_elapsed_ms / 1000, 3)

    @property
    def success_count(self) -> int:
        return sum(1 for e in self.engines if e.succeeded)

    @property
    def failure_count(self) -> int:
        return len(self.failed_engines)

    def to_dict(self) -> dict:
        return {
            "run_id":           self.run_id,
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "total_elapsed_sec": self.total_elapsed_sec,
            "all_success":      self.all_success,
            "success_count":    self.success_count,
            "failure_count":    self.failure_count,
            "failed_engines":   self.failed_engines,
            "engines":          [e.to_dict() for e in self.engines],
        }
