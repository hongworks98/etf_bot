"""
engines/breadth/market_breadth_engine.py
MarketBreadthEngine — Analysis Layer 신규 추가 Engine

"현재 시장 상승이 얼마나 건강한가?"를 정량적으로 평가.
기존 Architecture 수정 없이 Analysis Layer에 추가.

사용 방법:
    engine = MarketBreadthEngine.from_yaml("config/breadth_weights.yaml")
    result = engine.analyze(breadth_input)

    # PortfolioDecisionEngine과 연동
    analysis = AnalysisResult(
        ticker="SPY",
        breadth_score=result.breadth_score,  # 0~100
        ...
    )

    print(result.summary())
    print(engine.explain(result))
"""

from __future__ import annotations

import os
import statistics
from datetime import datetime
from typing import List, Optional

import yaml

from engines.breadth.analyzers.divergence_detector import DivergenceDetector
from engines.breadth.analyzers.trend_analyzer import TrendAnalyzer
from engines.breadth.calculators.advance_decline import AdvanceDeclineCalculator
from engines.breadth.calculators.base import AbstractBreadthCalculator
from engines.breadth.calculators.breadth_thrust import BreadthThrustCalculator
from engines.breadth.calculators.ma_breadth import MABreadthCalculator
from engines.breadth.calculators.new_high_low import NewHighLowCalculator
from engines.breadth.calculators.participation import ParticipationCalculator
from engines.breadth.data_models import (
    BreadthConfig,
    BreadthInput,
    BreadthResult,
    ComponentScore,
    HealthLevel,
)


class MarketBreadthEngine:
    """
    시장 폭 분석 Engine (Analysis Layer)

    책임:
    1. YAML에서 BreadthConfig 로드
    2. 5개 Calculator 실행 (8개 ComponentScore 생성)
    3. 가중합으로 breadth_score 계산
    4. TrendAnalyzer로 추세 분석
    5. DivergenceDetector로 괴리 탐지
    6. HealthLevel 결정 + Confidence + Reasons/Warnings 생성
    7. BreadthResult 조립 반환

    기존 Engine 절대 수정 없음.
    """

    def __init__(
        self,
        config: BreadthConfig,
        calculators: Optional[List[AbstractBreadthCalculator]] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        divergence_detector: Optional[DivergenceDetector] = None,
    ):
        self._config = config
        self._calculators = calculators or [
            AdvanceDeclineCalculator(),
            NewHighLowCalculator(),
            MABreadthCalculator(),
            ParticipationCalculator(),
            BreadthThrustCalculator(),
        ]
        self._trend_analyzer = trend_analyzer or TrendAnalyzer()
        self._divergence_detector = divergence_detector or DivergenceDetector()

    # ── 팩토리 ────────────────────────────────

    @classmethod
    def from_yaml(cls, config_path: str = "config/breadth_weights.yaml") -> "MarketBreadthEngine":
        """YAML에서 설정을 로드해 Engine 생성. 파일 없으면 기본값 사용."""
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        else:
            print(f"[MarketBreadthEngine] 경고: {config_path} 없음 → 기본값 사용")
            raw = {}

        config = cls._build_config(raw)
        return cls(config=config)

    @staticmethod
    def _build_config(raw: dict) -> BreadthConfig:
        """YAML dict → BreadthConfig"""
        cfg = BreadthConfig()

        if "component_weights" in raw:
            cfg.component_weights = raw["component_weights"]
        if "normalization" in raw:
            cfg.normalization = raw["normalization"]

        ht = raw.get("health_thresholds", {})
        cfg.health_excellent = ht.get("excellent", 75.0)
        cfg.health_healthy   = ht.get("healthy", 55.0)
        cfg.health_weakening = ht.get("weakening", 35.0)

        dv = raw.get("divergence", {})
        cfg.divergence_lookback         = dv.get("lookback_days", 20)
        cfg.index_move_threshold        = dv.get("index_move_threshold", 2.0)
        cfg.breadth_move_threshold      = dv.get("breadth_move_threshold", 5.0)
        cfg.divergence_strong_threshold = dv.get("strong_threshold", 50.0)

        tr = raw.get("trend", {})
        cfg.period_1m            = tr.get("period_1m", 21)
        cfg.period_3m            = tr.get("period_3m", 63)
        cfg.period_6m            = tr.get("period_6m", 126)
        cfg.acceleration_weight  = tr.get("acceleration_weight", 0.3)
        cfg.slope_normalize_lo   = tr.get("slope_normalize_lo", -3.0)
        cfg.slope_normalize_hi   = tr.get("slope_normalize_hi", 3.0)

        bt = raw.get("breadth_thrust", {})
        cfg.ema_period       = bt.get("ema_period", 10)
        cfg.thrust_signal_hi = bt.get("thrust_signal_hi", 61.5)
        cfg.thrust_signal_lo = bt.get("thrust_signal_lo", 40.0)

        co = raw.get("confidence", {})
        cfg.min_history_days  = co.get("min_history_days", 10)
        cfg.full_history_days = co.get("full_history_days", 63)
        cfg.variance_penalty  = co.get("variance_penalty", 0.5)

        return cfg

    # ── 핵심 메서드 ──────────────────────────────

    def analyze(self, inp: BreadthInput) -> BreadthResult:
        """
        시장 폭 분석 실행.

        Args:
            inp: BreadthInput (오늘 데이터 + 히스토리)

        Returns:
            BreadthResult (breadth_score, health, trend, divergence, ...)
        """
        # Step 1. 모든 Calculator 실행 → ComponentScore 목록
        all_scores: List[ComponentScore] = []
        for calc in self._calculators:
            all_scores.extend(calc.calculate(inp, self._config))

        # Step 2. 가중합 → breadth_score
        breadth_score = sum(s.contribution for s in all_scores)
        breadth_score = max(0.0, min(100.0, breadth_score))

        # Step 3. Health Level
        health_level = self._determine_health(breadth_score)

        # Step 4. Trend Analysis
        # 히스토리의 AD Ratio 시계열로 Trend 계산
        ad_ratios = [d.ad_ratio for d in inp.history] + [inp.current.ad_ratio]
        # breadth_score 시계열이 없으면 AD Ratio 시계열로 근사
        trend = self._trend_analyzer.analyze(inp, self._config, ad_ratios)

        # Step 5. Divergence Detection
        divergence = self._divergence_detector.detect(inp, self._config)

        # Step 6. Participation Score (별도 추출)
        participation_score = next(
            (s.normalized_score for s in all_scores if s.name == "participation"),
            50.0,
        )

        # Step 7. Confidence
        confidence = self._calculate_confidence(all_scores, inp)

        # Step 8. Reasons + Warnings
        reasons  = self._generate_reasons(breadth_score, health_level, trend, divergence, all_scores)
        warnings = self._generate_warnings(breadth_score, health_level, trend, divergence, all_scores, inp)

        return BreadthResult(
            breadth_score      = round(breadth_score, 2),
            health_level       = health_level,
            trend              = trend,
            participation_score= round(participation_score, 2),
            divergence         = divergence,
            confidence         = round(confidence, 3),
            component_scores   = all_scores,
            reasons            = reasons,
            warnings           = warnings,
            timestamp          = datetime.now(),
        )

    def get_breadth_score(self, inp: BreadthInput) -> float:
        """PortfolioDecisionEngine의 AnalysisResult.breadth_score 공급용 단축 메서드"""
        return self.analyze(inp).breadth_score

    # ── 내부 로직 ────────────────────────────────

    def _determine_health(self, score: float) -> HealthLevel:
        if score >= self._config.health_excellent:
            return HealthLevel.EXCELLENT
        elif score >= self._config.health_healthy:
            return HealthLevel.HEALTHY
        elif score >= self._config.health_weakening:
            return HealthLevel.WEAKENING
        else:
            return HealthLevel.CRITICAL

    def _calculate_confidence(
        self,
        scores: List[ComponentScore],
        inp: BreadthInput,
    ) -> float:
        """
        신뢰도 = 데이터 충분성 × 점수 일관성
        """
        # 데이터 충분성 (히스토리가 많을수록 1.0에 수렴)
        n_history = len(inp.history)
        data_factor = min(
            n_history / max(self._config.full_history_days, 1),
            1.0,
        )
        if n_history < self._config.min_history_days:
            data_factor *= 0.5

        # 점수 일관성 (표준편차가 낮을수록 신뢰도 높음)
        normalized_scores = [s.normalized_score for s in scores]
        if len(normalized_scores) > 1:
            std = statistics.stdev(normalized_scores)
            variance_factor = 1.0 - (std / 100.0) * self._config.variance_penalty
        else:
            variance_factor = 0.75

        return max(0.0, min(1.0, data_factor * variance_factor))

    def _generate_reasons(
        self,
        score: float,
        health: HealthLevel,
        trend,
        divergence,
        scores: List[ComponentScore],
    ) -> List[str]:
        """Explainable AI — 결정 근거 생성"""
        reasons = []

        # 1. 핵심 점수
        reasons.append(
            f"종합 Breadth Score {score:.1f}/100 — {health.value}"
        )

        # 2. 가장 강한 지표 (상위 2개)
        top2 = sorted(scores, key=lambda s: s.normalized_score, reverse=True)[:2]
        for s in top2:
            if s.normalized_score >= 65:
                reasons.append(s.interpretation)

        # 3. 추세
        reasons.append(
            f"시장 폭 추세: {trend.direction.value} | "
            f"1M 기울기 {trend.slope_1m:+.3f}/일 | "
            f"가속도 {trend.acceleration:+.3f}"
        )

        # 4. 200MA (핵심 지표)
        ma200 = next((s for s in scores if s.name == "pct_above_200ma"), None)
        if ma200:
            reasons.append(ma200.interpretation)

        return reasons[:5]

    def _generate_warnings(
        self,
        score: float,
        health: HealthLevel,
        trend,
        divergence,
        scores: List[ComponentScore],
        inp: BreadthInput,
    ) -> List[str]:
        """주의사항 생성"""
        warnings = []

        # Divergence 경고 (최우선)
        if divergence.type.value == "Bearish":
            prefix = "⚠ 강력 경고" if divergence.is_strong else "⚠ 주의"
            warnings.append(f"{prefix}: {divergence.description}")

        if divergence.type.value == "Bullish":
            warnings.append(f"★ 기회 신호: {divergence.description}")

        # Critical 상태
        if health == HealthLevel.CRITICAL:
            warnings.append("시장 폭 CRITICAL — 신규 매수 자제, 리스크 관리 최우선")

        # 추세 역전
        if trend.acceleration < -0.5:
            warnings.append(
                f"폭 개선 속도 감소 (가속도 {trend.acceleration:+.3f}) — "
                f"단기 반전 가능성 모니터링"
            )

        # 20MA vs 200MA 괴리 (단기 과열/과매도)
        ma20 = next((s for s in scores if s.name == "pct_above_20ma"), None)
        ma200 = next((s for s in scores if s.name == "pct_above_200ma"), None)
        if ma20 and ma200:
            gap = ma20.raw_value - ma200.raw_value
            if gap > 25:
                warnings.append(
                    f"단기 과열: 20MA 상회 {ma20.raw_value:.0f}% vs "
                    f"200MA 상회 {ma200.raw_value:.0f}% (괴리 {gap:.0f}%p) — 단기 조정 경계"
                )
            elif gap < -20:
                warnings.append(
                    f"단기 과매도: 20MA 상회 {ma20.raw_value:.0f}% vs "
                    f"200MA 상회 {ma200.raw_value:.0f}% — 기술적 반등 가능성"
                )

        # 데이터 부족
        if len(inp.history) < self._config.min_history_days:
            warnings.append(f"히스토리 {len(inp.history)}일 — 데이터 부족, 신뢰도 낮음")

        return warnings[:4]

    # ── 디버그 헬퍼 ──────────────────────────────

    def explain(self, result: BreadthResult) -> str:
        """전체 분석 결과를 사람이 읽기 쉬운 형태로 출력"""
        lines = [
            f"{'='*55}",
            f"  Market Breadth Engine — 분석 결과",
            f"{'='*55}",
            f"  Breadth Score : {result.breadth_score:.1f}/100",
            f"  Health Level  : {result.health_level.value}",
            f"  Confidence    : {result.confidence:.0%}",
            f"  Participation : {result.participation_score:.1f}/100",
            f"",
            f"  Trend : {result.trend.summary()}",
            f"",
            f"  Divergence: {result.divergence.description}",
            f"",
            f"{'─'*55}",
            f"  Component Scores (Explainable AI)",
            f"{'─'*55}",
        ]
        for s in result.component_scores:
            bar = "█" * int(s.normalized_score / 10)
            lines.append(
                f"  {s.direction} {s.name:<20} {s.normalized_score:5.1f}pt "
                f"×{s.weight:.2f} = {s.contribution:5.1f}  {bar}"
            )
            lines.append(f"     └─ {s.interpretation}")

        lines.append(f"{'─'*55}")
        lines.append(f"  {'TOTAL':22} {result.breadth_score:5.1f}/100")

        lines.append(f"\n{'─'*55}")
        lines.append("  Reasons:")
        for i, r in enumerate(result.reasons, 1):
            lines.append(f"    {i}. {r}")

        if result.warnings:
            lines.append(f"\n{'─'*55}")
            lines.append("  Warnings:")
            for w in result.warnings:
                lines.append(f"    {w}")

        lines.append(f"{'='*55}")
        return "\n".join(lines)
