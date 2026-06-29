"""
engines/rotation/rotation_signal_engine.py
RotationSignalEngine — Main Orchestrator (Analysis Layer, Step 5)

4-Phase Pipeline:
  Phase 1: per-ETF signal calculation
  Phase 2: cross-ETF analysis (ranking, opportunity, risk)
  Phase 3: XAI, forecast, timing, conviction
  Phase 4: aggregation — directions, cost analysis, dashboard
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import yaml

from engines.rotation.calculators.capital_flow_calculator import CapitalFlowCalculator
from engines.rotation.calculators.conviction_calculator import ConvictionCalculator
from engines.rotation.calculators.lifecycle_calculator import LifecycleCalculator
from engines.rotation.calculators.opportunity_calculator import OpportunityCalculator
from engines.rotation.calculators.rotation_score_calculator import RotationScoreCalculator
from engines.rotation.analyzers.dashboard_builder import DashboardBuilder
from engines.rotation.analyzers.false_rotation_detector import FalseRotationDetector
from engines.rotation.analyzers.rotation_attribution import RotationAttributionAnalyzer
from engines.rotation.analyzers.rotation_forecast import RotationForecastAnalyzer
from engines.rotation.analyzers.rotation_risk import RotationRiskAnalyzer
from engines.rotation.analyzers.rotation_timing import RotationTimingAnalyzer
from engines.rotation.data_models import (
    ConvictionLevel, RotationAttribution, RotationConfig, RotationDirection,
    RotationEngineResult, RotationInput, RotationResult,
    RotationSpeedLevel, RotationStage, RotationStrength,
)


class RotationSignalEngine:
    """
    Analysis Layer Engine: Rotation Intelligence for Sector Rotation.
    Integrates Macro / Breadth / RS / Trend / Capital Flow signals.
    Outputs RotationEngineResult → feeds PortfolioDecisionEngine.
    Existing engines are NEVER modified — only their outputs are read.
    """

    def __init__(
        self,
        config: RotationConfig,
        score_calc:      Optional[RotationScoreCalculator]    = None,
        flow_calc:       Optional[CapitalFlowCalculator]      = None,
        lifecycle_calc:  Optional[LifecycleCalculator]        = None,
        conviction_calc: Optional[ConvictionCalculator]       = None,
        opp_calc:        Optional[OpportunityCalculator]      = None,
        false_detector:  Optional[FalseRotationDetector]      = None,
        attribution:     Optional[RotationAttributionAnalyzer]= None,
        forecast:        Optional[RotationForecastAnalyzer]   = None,
        timing:          Optional[RotationTimingAnalyzer]     = None,
        risk:            Optional[RotationRiskAnalyzer]       = None,
        dashboard:       Optional[DashboardBuilder]           = None,
    ) -> None:
        self._cfg  = config
        self._score   = score_calc      or RotationScoreCalculator()
        self._flow    = flow_calc       or CapitalFlowCalculator()
        self._life    = lifecycle_calc  or LifecycleCalculator()
        self._conv    = conviction_calc or ConvictionCalculator()
        self._opp     = opp_calc        or OpportunityCalculator()
        self._false   = false_detector  or FalseRotationDetector()
        self._attr    = attribution     or RotationAttributionAnalyzer()
        self._fore    = forecast        or RotationForecastAnalyzer()
        self._time    = timing          or RotationTimingAnalyzer()
        self._risk    = risk            or RotationRiskAnalyzer()
        self._dash    = dashboard       or DashboardBuilder()

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, config_path: str = "config/rotation_weights.yaml") -> "RotationSignalEngine":
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            config = RotationConfig.from_dict(raw)
        else:
            config = RotationConfig()
        return cls(config=config)

    # ── Public API ────────────────────────────────────────────────────────

    def analyze_all(self, inp: RotationInput) -> RotationEngineResult:
        """Full sector rotation analysis across all ETFs."""
        if not inp.sectors:
            return RotationEngineResult()

        cfg = self._cfg

        # ── Phase 1: per-ETF base calculations ───────────────────────────
        phase1: Dict[str, dict] = {}
        for ticker in inp.sectors:
            history      = inp.previous_rotation_scores.get(ticker, [])
            prev_stage   = inp.previous_rotation_state.get(ticker, "Building")

            capital_flow = self._flow.calculate(ticker, inp, cfg)

            # Risk needed for rotation score
            stage_prev   = self._str_to_stage(prev_stage)
            risk_score   = self._risk.compute(ticker, 50.0, history, stage_prev, inp, cfg)

            rotation_score, attributions = self._score.calculate(
                ticker, inp, capital_flow, risk_score, cfg)

            phase1[ticker] = dict(
                rotation_score=rotation_score,
                capital_flow=capital_flow,
                risk_score=risk_score,
                attributions=attributions,
                history=history,
                prev_stage=prev_stage,
            )

        # ── Phase 2: lifecycle, false detection, opportunity ─────────────
        phase2: Dict[str, dict] = {}
        for ticker, d in phase1.items():
            stage, persist_days, persist_weeks, stability = self._life.calculate(
                d["rotation_score"], d["history"], d["prev_stage"], cfg)

            is_false, false_reason = self._false.detect(
                ticker, d["rotation_score"], d["history"], persist_days, inp, cfg)

            opp_score = self._opp.calculate(
                ticker, inp.current_holdings, d["rotation_score"],
                inp.get_persistence_score(ticker), 50.0,   # conviction not yet known
                inp, cfg)

            # Updated risk with actual stage
            risk_score = self._risk.compute(
                ticker, d["rotation_score"], d["history"], stage, inp, cfg)

            confidence = self._risk.confidence_from_signals(
                ticker, d["rotation_score"], d["capital_flow"], stage, inp, cfg)

            phase2[ticker] = {
                **d,
                "stage": stage,
                "persist_days": persist_days,
                "persist_weeks": persist_weeks,
                "stability": stability,
                "is_false": is_false,
                "false_reason": false_reason,
                "opp_score": opp_score,
                "risk_score": risk_score,
                "confidence": confidence,
            }

        # ── Phase 3: XAI, forecast, timing, conviction ───────────────────
        results: Dict[str, RotationResult] = {}
        for ticker, d in phase2.items():
            # Attribution XAI
            sorted_attr, xai_summary, _ = self._attr.analyze(
                d["attributions"], d["rotation_score"], cfg)

            # Forecast
            forecast_score = self._fore.compute(
                ticker, d["capital_flow"], inp, cfg)

            # Speed
            speed_score, speed_level = self._compute_speed(
                d["rotation_score"], d["history"], cfg)

            # Timing (preliminary, no conviction yet)
            timing_prelim = self._time.determine(
                d["rotation_score"], ConvictionLevel.OBSERVE,
                d["stage"], forecast_score, d["is_false"], cfg)

            # Conviction
            conviction_score, conviction_level = self._conv.calculate(
                d["rotation_score"], d["confidence"], d["stage"],
                d["opp_score"], timing_prelim, cfg)

            # Final timing with actual conviction
            timing = self._time.determine(
                conviction_score, conviction_level,
                d["stage"], forecast_score, d["is_false"], cfg)

            # Strength
            strength = self._score_to_strength(d["rotation_score"], cfg)

            # XAI narrative
            triggers = self._attr.build_triggers(
                sorted_attr, inp.macro_state, inp.breadth_health)
            reasons, warnings, why_now, why_etf = self._build_narrative(
                ticker, d, conviction_level, timing, forecast_score, inp, cfg)

            results[ticker] = RotationResult(
                ticker=ticker,
                rotation_score=round(d["rotation_score"], 2),
                stage=d["stage"],
                strength=strength,
                timing=timing,
                speed=round(speed_score, 2),
                speed_level=speed_level,
                persistence_days=d["persist_days"],
                persistence_weeks=d["persist_weeks"],
                confidence=round(d["confidence"], 2),
                forecast=round(forecast_score, 2),
                opportunity_score=round(d["opp_score"], 2),
                capital_flow_score=round(d["capital_flow"], 2),
                conviction_score=round(conviction_score, 2),
                conviction_level=conviction_level,
                stability=round(d["stability"], 2),
                rotation_risk=round(d["risk_score"], 2),
                is_false_rotation=d["is_false"],
                false_rotation_reason=d["false_reason"],
                attribution=sorted_attr,
                triggers=triggers,
                reasons=reasons,
                warnings=warnings,
                why_now=why_now,
                why_this_etf=why_etf,
                xai_summary=xai_summary,
            )

        # ── Phase 4: aggregation ─────────────────────────────────────────
        directions   = self._detect_directions(results, cfg)
        top_opps     = sorted(results, key=lambda t: results[t].opportunity_score, reverse=True)
        conv_ranking = sorted(results, key=lambda t: results[t].conviction_score, reverse=True)
        market_active = bool(directions)
        dominant      = directions[0] if directions else None

        # Cost analysis (for held positions)
        cost_analysis = {}
        if inp.current_holdings:
            for to_t in top_opps[:5]:
                for from_t in inp.current_holdings:
                    if from_t != to_t:
                        key = f"{from_t}→{to_t}"
                        cost_analysis[key] = self._opp.build_cost_analysis(
                            from_t, to_t,
                            results[to_t].opportunity_score if to_t in results else 50.0,
                            results.get(from_t, RotationResult(ticker=from_t)).rotation_score,
                            inp, cfg,
                        )

        dashboard_data = self._dash.build(results, directions, cfg)

        return RotationEngineResult(
            sector_results=results,
            rotation_directions=directions,
            top_opportunities=top_opps,
            conviction_rankings=conv_ranking,
            dashboard_data=dashboard_data,
            cost_analysis=cost_analysis,
            market_rotation_active=market_active,
            dominant_rotation=dominant,
        )

    def analyze(self, ticker: str, inp: RotationInput) -> RotationResult:
        """Single-ETF shortcut."""
        if ticker not in inp.sectors:
            return RotationResult(ticker=ticker)
        single = RotationInput(
            spy=inp.spy,
            sectors={ticker: inp.sectors[ticker]},
            sector_volumes={ticker: inp.sector_volumes.get(ticker, [])},
            breadth_score=inp.breadth_score,
            breadth_health=inp.breadth_health,
            breadth_trend=inp.breadth_trend,
            rs_results={ticker: inp.rs_results.get(ticker)} if ticker in inp.rs_results else {},
            trend_data={ticker: inp.trend_data[ticker]} if ticker in inp.trend_data else {},
            macro_state=inp.macro_state,
            macro_score=inp.macro_score,
            macro_direction=inp.macro_direction,
            market_health_score=inp.market_health_score,
            aux_data=inp.aux_data,
            current_holdings=inp.current_holdings,
            portfolio_value=inp.portfolio_value,
            previous_rotation_scores={ticker: inp.previous_rotation_scores.get(ticker, [])},
            previous_rotation_state={ticker: inp.previous_rotation_state.get(ticker, "Building")},
            transaction_cost_pct=inp.transaction_cost_pct,
        )
        result = self.analyze_all(single)
        return result.sector_results.get(ticker, RotationResult(ticker=ticker))

    def explain(self, result: RotationResult) -> str:
        """Full XAI explanation for one ETF rotation result."""
        lines = [
            f"═══ Rotation Analysis: {result.ticker} ═══",
            f"Rotation Score : {result.rotation_score:.1f}/100",
            f"Stage          : {result.stage.value}",
            f"Strength       : {result.strength.value}",
            f"Conviction     : {result.conviction_score:.1f} → {result.conviction_level.value}",
            f"Timing         : {result.timing.value}",
            f"Speed          : {result.speed:.1f} ({result.speed_level.value})",
            f"Persistence    : {result.persistence_days}d / {result.persistence_weeks}wk",
            f"Confidence     : {result.confidence:.1f}",
            f"Forecast       : {result.forecast:.1f}",
            f"Capital Flow   : {result.capital_flow_score:.1f}",
            f"Rotation Risk  : {result.rotation_risk:.1f}",
            f"Stability      : {result.stability:.1f}",
        ]
        if result.is_false_rotation:
            lines.append(f"⚠ FALSE ROTATION: {result.false_rotation_reason}")
        lines += ["", "Why Rotation:", f"  {result.why_this_etf}"]
        lines += ["", "Why Now:", f"  {result.why_now}"]
        if result.triggers:
            lines += ["", "Triggers:"] + [f"  • {t}" for t in result.triggers]
        if result.reasons:
            lines += ["", "Signals:"] + [f"  + {r}" for r in result.reasons]
        if result.warnings:
            lines += ["", "Warnings:"] + [f"  ! {w}" for w in result.warnings]
        lines += ["", "Attribution (Rotation Decomposition):"]
        for a in result.attribution:
            lines.append(
                f"  {a.direction} {a.factor:20s}: {a.pct_contribution:5.1f}%"
                f"  (raw={a.score_contribution:.3f})"
            )
        lines += ["", f"XAI Summary: {result.xai_summary}"]
        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _str_to_stage(s: str) -> RotationStage:
        mapping = {
            "Emerging": RotationStage.EMERGING, "Building": RotationStage.BUILDING,
            "Confirmed": RotationStage.CONFIRMED, "Mature": RotationStage.MATURE,
            "Weakening": RotationStage.WEAKENING, "Reversing": RotationStage.REVERSING,
        }
        return mapping.get(s, RotationStage.BUILDING)

    @staticmethod
    def _score_to_strength(score: float, cfg: RotationConfig) -> RotationStrength:
        if score >= cfg.extreme_threshold:
            return RotationStrength.EXTREME
        if score >= cfg.strong_threshold:
            return RotationStrength.STRONG
        if score >= cfg.moderate_threshold:
            return RotationStrength.MODERATE
        return RotationStrength.WEAK

    @staticmethod
    def _compute_speed(
        current_score: float, history: List[float], cfg: RotationConfig
    ) -> Tuple[float, RotationSpeedLevel]:
        """Speed = normalized rate of score change over speed_lookback days."""
        if len(history) < cfg.speed_lookback:
            return 50.0, RotationSpeedLevel.MODERATE
        delta = abs(current_score - history[-cfg.speed_lookback])
        speed_score = min(100.0, delta / 30.0 * 100.0)  # 30 points/week → max speed
        if speed_score >= cfg.rapid_speed:
            return speed_score, RotationSpeedLevel.RAPID
        if speed_score >= cfg.fast_speed:
            return speed_score, RotationSpeedLevel.FAST
        if speed_score >= cfg.moderate_speed:
            return speed_score, RotationSpeedLevel.MODERATE
        return speed_score, RotationSpeedLevel.SLOW

    def _detect_directions(
        self,
        results: Dict[str, RotationResult],
        cfg: RotationConfig,
    ) -> List[RotationDirection]:
        """Detect FROM→TO capital flow pairs."""
        into_sectors = [t for t, r in results.items()
                        if r.rotation_score >= cfg.into_threshold and not r.is_false_rotation]
        out_sectors  = [t for t, r in results.items()
                        if r.rotation_score <= cfg.out_threshold and not r.is_false_rotation]

        directions: List[RotationDirection] = []
        for from_t in out_sectors:
            for to_t in into_sectors:
                score_from = results[from_t].rotation_score
                score_to   = results[to_t].rotation_score
                gap        = score_to - score_from
                confidence = min(1.0, gap / 60.0)

                if confidence < cfg.min_dir_confidence:
                    continue

                if gap >= 50:
                    strength = RotationStrength.EXTREME
                elif gap >= 35:
                    strength = RotationStrength.STRONG
                elif gap >= 20:
                    strength = RotationStrength.MODERATE
                else:
                    strength = RotationStrength.WEAK

                directions.append(RotationDirection(
                    from_sector=from_t,
                    to_sector=to_t,
                    strength=strength,
                    confidence=round(confidence, 2),
                    rotation_score_from=round(score_from, 1),
                    rotation_score_to=round(score_to, 1),
                    description=(
                        f"Capital appears to be rotating from {from_t} "
                        f"(score={score_from:.0f}) to {to_t} (score={score_to:.0f}). "
                        f"Gap={gap:.0f}, Confidence={confidence:.0%}"
                    ),
                ))

        # Sort by confidence desc
        directions.sort(key=lambda d: d.confidence, reverse=True)
        return directions

    @staticmethod
    def _build_narrative(
        ticker: str, d: dict, conviction: ConvictionLevel,
        timing, forecast: float, inp: RotationInput, cfg: RotationConfig,
    ) -> Tuple[List[str], List[str], str, str]:
        reasons, warnings = [], []

        if conviction in {ConvictionLevel.IMMEDIATE_ROTATION, ConvictionLevel.GRADUAL_ROTATION}:
            reasons.append(f"High conviction signal: {conviction.value}")
        if d["stage"] in {RotationStage.CONFIRMED, RotationStage.BUILDING}:
            reasons.append(f"Rotation in {d['stage'].value} stage with {d['persist_days']} active days")
        if d["capital_flow"] >= 60:
            reasons.append(f"Capital flowing in (flow={d['capital_flow']:.1f})")
        if forecast >= 65:
            reasons.append(f"Forward-looking forecast strong ({forecast:.0f}/100)")

        if d["stage"] in {RotationStage.WEAKENING, RotationStage.REVERSING}:
            warnings.append(f"Stage is {d['stage'].value} — rotation may be ending")
        if d["risk_score"] >= 60:
            warnings.append(f"Elevated rotation risk ({d['risk_score']:.1f})")
        if inp.aux_data.latest_vix() >= cfg.vix_high:
            warnings.append(f"VIX elevated ({inp.aux_data.latest_vix():.1f}) — risk-off environment")
        if d["is_false"]:
            warnings.append(f"False rotation flag: {d['false_reason']}")

        # Macro
        expected = cfg.macro_expected_leaders.get(inp.macro_state, [])
        macro_fit = ticker in expected
        why_etf = (
            f"{ticker} is {'an expected' if macro_fit else 'an unexpected'} leader "
            f"in {inp.macro_state} phase with RS={inp.get_rs_score(ticker):.1f} "
            f"and rotation score={d['rotation_score']:.1f}."
        )
        why_now = (
            f"Timing recommendation is {timing.value}. "
            f"Conviction={d.get('conviction_score', d['rotation_score']):.1f}, "
            f"Stage={d['stage'].value}, Forecast={forecast:.0f}."
        )
        return reasons, warnings, why_now, why_etf
