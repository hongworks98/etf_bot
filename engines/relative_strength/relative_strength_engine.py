"""
engines/relative_strength/relative_strength_engine.py
RelativeStrengthEngine — Main Orchestrator (Analysis Layer, Step 4)
4-Phase pipeline:
  Phase 1: per-ETF calculators (MultiTimeframe, Trend, Persistence, Quality)
  Phase 2: cross-ETF ranking
  Phase 3: per-ETF assembly (Leadership, RotationReadiness, MacroValidation, XAI)
  Phase 4: portfolio-level aggregation + Heatmap
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import yaml

from engines.relative_strength.calculators.multi_timeframe import MultiTimeframeCalculator
from engines.relative_strength.calculators.persistence_calculator import PersistenceCalculator
from engines.relative_strength.calculators.quality_calculator import QualityCalculator
from engines.relative_strength.calculators.trend_calculator import RSTrendCalculator
from engines.relative_strength.analyzers.heatmap_builder import HeatmapBuilder
from engines.relative_strength.analyzers.leadership_detector import LeadershipDetector
from engines.relative_strength.analyzers.macro_validator import MacroValidator
from engines.relative_strength.analyzers.ranking_engine import RankingEngine
from engines.relative_strength.analyzers.rotation_readiness import RotationReadinessAnalyzer
from engines.relative_strength.data_models import (
    PriceHistory, RSConfig, RSContribution, RSEngineResult,
    RSInput, RelativeStrengthResult,
)


class RelativeStrengthEngine:
    """
    Analysis Layer Engine: Sector Rotation RS Analysis.
    All weights/thresholds managed externally via YAML.
    All sub-components injected via constructor (DIP).
    """

    def __init__(
        self,
        config: RSConfig,
        mtf_calculator:     Optional[MultiTimeframeCalculator]  = None,
        trend_calculator:   Optional[RSTrendCalculator]         = None,
        persistence_calc:   Optional[PersistenceCalculator]     = None,
        quality_calculator: Optional[QualityCalculator]         = None,
        ranking_engine:     Optional[RankingEngine]             = None,
        leadership_detector: Optional[LeadershipDetector]       = None,
        rotation_readiness: Optional[RotationReadinessAnalyzer] = None,
        macro_validator:    Optional[MacroValidator]            = None,
        heatmap_builder:    Optional[HeatmapBuilder]            = None,
    ) -> None:
        self._config = config

        # Calculators (DIP: default concrete → easily mocked in tests)
        self._mtf         = mtf_calculator     or MultiTimeframeCalculator()
        self._trend       = trend_calculator   or RSTrendCalculator()
        self._persistence = persistence_calc   or PersistenceCalculator()
        self._quality     = quality_calculator or QualityCalculator()

        # Analyzers
        self._ranking    = ranking_engine      or RankingEngine()
        self._leadership = leadership_detector or LeadershipDetector()
        self._rotation   = rotation_readiness  or RotationReadinessAnalyzer()
        self._macro      = macro_validator     or MacroValidator()
        self._heatmap    = heatmap_builder     or HeatmapBuilder()

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, config_path: str = "config/rs_weights.yaml") -> "RelativeStrengthEngine":
        """Production factory: loads RSConfig from YAML then instantiates engine."""
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            config = RSConfig.from_dict(raw)
        else:
            config = RSConfig()
        return cls(config=config)

    # ── Public API ────────────────────────────────────────────────────────

    def analyze_all(self, inp: RSInput) -> RSEngineResult:
        """
        Full sector RS analysis.
        Returns RSEngineResult with per-sector results, rankings, heatmap.
        """
        if not inp.sectors:
            return RSEngineResult()

        # ── Phase 1: per-ETF calculators ─────────────────────────────────
        phase1: Dict[str, dict] = {}    # {ticker: {composite_rs, timeframes, trend, persistence, quality, contributions}}
        for ticker, etf in inp.sectors.items():
            composite_rs, timeframes, mtf_contributions = self._mtf.calculate(etf, inp.spy, self._config)
            trend, trend_contributions                  = self._trend.calculate(etf, inp.spy, self._config)
            persistence, persist_contributions          = self._persistence.calculate(etf, inp.spy, self._config)
            tf_rs_scores = [tf.rs_score for tf in timeframes]
            quality, quality_contributions              = self._quality.calculate(etf, inp.spy, tf_rs_scores, persistence, self._config)

            phase1[ticker] = dict(
                composite_rs=composite_rs,
                timeframes=timeframes,
                trend=trend,
                persistence=persistence,
                quality=quality,
                contributions=mtf_contributions + trend_contributions + persist_contributions + quality_contributions,
            )

        # ── Phase 2: cross-ETF ranking ────────────────────────────────────
        scores = {t: d["composite_rs"] for t, d in phase1.items()}
        rank_infos = self._ranking.rank(scores, inp.previous_rankings, self._config)
        sorted_tickers = self._ranking.sorted_rankings(rank_infos)

        # ── Phase 3: per-ETF assembly ─────────────────────────────────────
        results: Dict[str, RelativeStrengthResult] = {}
        for ticker, d in phase1.items():
            rank_info    = rank_infos[ticker]
            leader_status = self._leadership.classify(d["composite_rs"], rank_info, self._config)

            # Previous persistence: 50 if no prior data
            prev_persistence = 50.0

            rotation = self._rotation.compute(
                rank_info=rank_info,
                trend=d["trend"],
                persistence_score=d["persistence"],
                previous_persistence=prev_persistence,
                breadth_score=inp.breadth_score,
                config=self._config,
            )

            macro_val = self._macro.validate(ticker, leader_status, inp.macro_state, self._config)

            # Final RS score: weighted blend of calculator outputs
            rsw = self._config.rs_score_weights
            rs_score = min(100.0, max(0.0,
                d["composite_rs"]          * rsw.get("composite_rs",   0.50) +
                d["trend"].trend_score     * rsw.get("trend_score",    0.20) +
                d["persistence"]           * rsw.get("persistence",    0.15) +
                d["quality"].quality_score * rsw.get("quality_score",  0.15)
            ))

            # Confidence
            confidence = self._compute_confidence(inp.spy, d["persistence"], self._config)

            # Reasons & warnings
            reasons, warnings = self._build_reasons(
                ticker, rs_score, leader_status, rank_info,
                d["trend"], macro_val, rotation,
            )
            if macro_val.warning:
                warnings.append(macro_val.warning)

            results[ticker] = RelativeStrengthResult(
                ticker=ticker,
                rs_score=round(rs_score, 2),
                timeframes=d["timeframes"],
                trend=d["trend"],
                rank=rank_info,
                leader_status=leader_status,
                persistence_score=round(d["persistence"], 2),
                quality=d["quality"],
                rotation_readiness=round(rotation, 2),
                macro_validation=macro_val,
                contributions=d["contributions"],
                confidence=round(confidence, 3),
                reasons=reasons,
                warnings=warnings,
            )

        # ── Phase 4: portfolio-level aggregation ──────────────────────────
        leaders   = [t for t in sorted_tickers if results[t].is_leader]
        followers = [t for t in sorted_tickers if results[t].leader_status.value == "Follower"]
        laggards  = [t for t in sorted_tickers if results[t].is_laggard]

        portfolio_rotation = (
            sum(results[t].rotation_readiness for t in leaders) / len(leaders)
            if leaders else 50.0
        )

        heatmap = self._heatmap.build(results, self._config)

        return RSEngineResult(
            sector_results=results,
            rankings=sorted_tickers,
            leaders=leaders,
            followers=followers,
            laggards=laggards,
            heatmap_data=heatmap,
            portfolio_rotation_signal=round(portfolio_rotation, 2),
        )

    def analyze(self, ticker: str, etf: PriceHistory, inp: RSInput) -> RelativeStrengthResult:
        """Single-ETF shortcut (wraps analyze_all with one sector)."""
        single_inp = RSInput(
            spy=inp.spy,
            sectors={ticker: etf},
            breadth_score=inp.breadth_score,
            macro_state=inp.macro_state,
            macro_direction=inp.macro_direction,
            previous_rankings=inp.previous_rankings,
        )
        engine_result = self.analyze_all(single_inp)
        return engine_result.sector_results.get(ticker, RelativeStrengthResult(ticker=ticker, rs_score=50.0))

    def get_rs_score(self, ticker: str, etf: PriceHistory, inp: RSInput) -> float:
        """Shortcut: returns only rs_score for AnalysisResult.rs_score."""
        return self.analyze(ticker, etf, inp).rs_score

    def explain(self, result: RelativeStrengthResult) -> str:
        """Human-readable explanation for Explainable AI output."""
        lines = [
            f"═══ RS Analysis: {result.ticker} ═══",
            f"RS Score      : {result.rs_score:.1f}/100",
            f"Status        : {result.leader_status.value}",
            f"Rank          : #{result.rank.current_rank}/{result.rank.total_sectors}"
            f"  (Δ{result.rank.rank_change:+d}{'  ★JUMP' if result.rank.rank_jump else ''})",
            f"Trend         : {result.trend.direction.value}"
            f"  (slope={result.trend.slope:+.5f}, accel={result.trend.acceleration:+.5f})",
            f"Persistence   : {result.persistence_score:.1f}",
            f"Quality       : {result.quality.quality_score:.1f}"
            f"  (consistency={result.quality.consistency:.0f},"
            f" vol={result.quality.volatility:.0f},"
            f" part={result.quality.participation:.0f})",
            f"Rotation Ready: {result.rotation_readiness:.1f}",
            f"Macro Aligned : {result.macro_validation.is_aligned}"
            f"  ({result.macro_validation.description[:60]}...)"
            if len(result.macro_validation.description) > 60
            else f"Macro Aligned : {result.macro_validation.is_aligned}"
                 f"  ({result.macro_validation.description})",
            f"Confidence    : {result.confidence:.0%}",
            "",
            "Timeframes:",
        ]
        for tf in result.timeframes:
            lines.append(
                f"  {tf.period:4s}: ETF={tf.etf_return:+.2f}%  SPY={tf.spy_return:+.2f}%"
                f"  Rel={tf.relative_return:+.2f}%  Score={tf.rs_score:.1f}"
            )
        if result.reasons:
            lines.append("\nSignals:")
            lines.extend(f"  + {r}" for r in result.reasons)
        if result.warnings:
            lines.append("\nWarnings:")
            lines.extend(f"  ! {w}" for w in result.warnings)
        lines.append("\nXAI Contributions (top 5):")
        top = sorted(result.contributions, key=lambda c: abs(c.contribution), reverse=True)[:5]
        for c in top:
            lines.append(
                f"  {c.direction} [{c.factor}]  raw={c.raw_value:.3f}"
                f"  wt={c.weight:.2f}  contrib={c.contribution:.2f}"
                f"  → {c.interpretation}"
            )
        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _compute_confidence(spy: PriceHistory, persistence_score: float, config: RSConfig) -> float:
        history_len = len(spy.prices)
        if history_len < config.min_history_days:
            data_conf = 0.3
        elif history_len >= config.full_history_days:
            data_conf = 1.0
        else:
            data_conf = 0.3 + 0.7 * (history_len - config.min_history_days) / (
                config.full_history_days - config.min_history_days
            )
        persist_conf = persistence_score / 100.0 * config.persistence_weight
        base         = data_conf * (1 - config.persistence_weight)
        return min(1.0, base + persist_conf)

    @staticmethod
    def _build_reasons(ticker, rs_score, leader_status, rank_info, trend, macro_val, rotation):
        reasons, warnings = [], []

        if leader_status.value == "Leader":
            reasons.append(f"{ticker} is a sector Leader with RS={rs_score:.1f}")
        elif leader_status.value == "Laggard":
            warnings.append(f"{ticker} is a Laggard with RS={rs_score:.1f}")

        if rank_info.rank_jump:
            reasons.append(f"Rank jumped {rank_info.rank_change:+d} positions (#{rank_info.current_rank})")
        elif rank_info.rank_change > 0:
            reasons.append(f"Rank improved {rank_info.rank_change:+d} to #{rank_info.current_rank}")
        elif rank_info.rank_change < 0:
            warnings.append(f"Rank declined {rank_info.rank_change:+d} to #{rank_info.current_rank}")

        if trend.direction.value == "Rising":
            reasons.append(f"RS trend Rising (slope={trend.slope:+.4f})")
        elif trend.direction.value == "Falling":
            warnings.append(f"RS trend Falling (slope={trend.slope:+.4f})")

        if macro_val.is_aligned:
            reasons.append("Macro-RS alignment confirmed")
        else:
            warnings.append("Macro-RS misalignment detected")

        if rotation >= 70:
            reasons.append(f"High rotation readiness ({rotation:.0f})")
        elif rotation <= 30:
            warnings.append(f"Low rotation readiness ({rotation:.0f})")

        return reasons, warnings
