"""
engines/decision/portfolio_decision_engine.py
PortfolioDecisionEngine — Analysis Layer와 Decision Layer를 연결하는 Brain

사용 방법:
    engine = PortfolioDecisionEngine.from_yaml("config/decision_weights.yaml")

    result = engine.decide(
        ticker="KODEX 반도체",
        analysis=analysis_result,
        portfolio_state=portfolio_state,
    )
    print(result.summary())

    # 여러 ETF 동시 처리 (priority 순 정렬)
    results = engine.decide_all(analysis_list, portfolio_state)

설계 원칙:
- 기존 Analysis Engine 절대 수정 없음 — 결과만 입력받음
- Dependency Injection: Calculator를 생성자로 주입 (테스트 친화적)
- from_yaml(): 프로덕션 사용 편의를 위한 팩토리 메서드
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

import yaml

from engines.decision.calculators.base import AbstractScoreCalculator
from engines.decision.calculators.buy_score import BuyScoreCalculator
from engines.decision.calculators.exit_score import ExitScoreCalculator
from engines.decision.calculators.hold_score import HoldScoreCalculator
from engines.decision.calculators.opportunity_score import OpportunityScoreCalculator
from engines.decision.data_models import (
    Action,
    ActionScore,
    AnalysisResult,
    DecisionConfig,
    DecisionResult,
    PortfolioState,
    ThresholdConfig,
)
from engines.decision.decision_matrix import DecisionMatrix


class PortfolioDecisionEngine:
    """
    Analysis Layer → Decision Layer 핵심 Brain

    책임:
    1. YAML에서 DecisionConfig 로드
    2. 4개 Calculator 실행 (buy / hold / exit / opportunity)
    3. DecisionMatrix로 Action 결정
    4. DecisionResult 조립 및 반환

    테스트 시 Calculator를 Mock으로 교체 가능 (DI).
    """

    def __init__(
        self,
        config: DecisionConfig,
        buy_calculator: Optional[AbstractScoreCalculator] = None,
        hold_calculator: Optional[AbstractScoreCalculator] = None,
        exit_calculator: Optional[AbstractScoreCalculator] = None,
        opportunity_calculator: Optional[AbstractScoreCalculator] = None,
        decision_matrix: Optional[DecisionMatrix] = None,
    ):
        self._config = config
        self._buy_calc  = buy_calculator  or BuyScoreCalculator()
        self._hold_calc = hold_calculator or HoldScoreCalculator()
        self._exit_calc = exit_calculator or ExitScoreCalculator()
        self._opp_calc  = opportunity_calculator or OpportunityScoreCalculator()
        self._matrix    = decision_matrix or DecisionMatrix()

    # ── 팩토리 ────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, config_path: str = "config/decision_weights.yaml") -> "PortfolioDecisionEngine":
        """
        YAML 파일에서 설정을 로드해 Engine을 생성한다.
        파일이 없으면 기본값으로 생성.
        """
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        else:
            print(f"[PortfolioDecisionEngine] 경고: {config_path} 없음 → 기본값 사용")
            raw = {}

        config = cls._build_config(raw)
        return cls(config=config)

    @staticmethod
    def _build_config(raw: dict) -> DecisionConfig:
        """YAML dict → DecisionConfig 변환"""
        th_raw = raw.get("thresholds", {})
        thresholds = ThresholdConfig(
            strong_buy         = th_raw.get("strong_buy", 75.0),
            buy                = th_raw.get("buy", 60.0),
            add                = th_raw.get("add", 55.0),
            hold_min           = th_raw.get("hold_min", 45.0),
            trim               = th_raw.get("trim", 60.0),
            sell               = th_raw.get("sell", 75.0),
            risk_override_sell = th_raw.get("risk_override_sell", 85.0),
            risk_override_trim = th_raw.get("risk_override_trim", 70.0),
        )

        pc = raw.get("portfolio_constraints", {})
        conf_raw = raw.get("confidence", {})
        ph = raw.get("position_health", {})
        align = raw.get("macro_align_scores", {})
        priority = raw.get("priority", {})

        return DecisionConfig(
            buy_score_weights         = raw.get("buy_score_weights", {}),
            hold_score_weights        = raw.get("hold_score_weights", {}),
            exit_score_weights        = raw.get("exit_score_weights", {}),
            opportunity_score_weights = raw.get("opportunity_score_weights", {}),
            thresholds                = thresholds,
            max_position_size         = pc.get("max_position_size", 0.30),
            max_sector_exposure       = pc.get("max_sector_exposure", 0.40),
            default_position_size     = pc.get("default_position_size", 0.10),
            min_position_size         = pc.get("min_position_size", 0.03),
            max_portfolio_positions   = int(pc.get("max_portfolio_positions", 10)),
            min_cash_pct              = pc.get("min_cash_pct", 0.05),
            pnl_multiplier            = ph.get("pnl_multiplier", 2.0),
            max_pnl_effect            = ph.get("max_pnl_effect", 40.0),
            macro_align_scores        = {
                "rank_1": align.get("rank_1", 100),
                "rank_2": align.get("rank_2", 80),
                "rank_3": align.get("rank_3", 60),
                "rank_4": align.get("rank_4", 40),
                "rank_5": align.get("rank_5", 20),
                "default": align.get("default", 0),
            },
            confidence_max_std = conf_raw.get("max_std_dev", 30.0),
            confidence_min_std = conf_raw.get("min_std_dev", 5.0),
            priority_map = {
                "BUY":  priority.get("BUY", 1),
                "ADD":  priority.get("ADD", 2),
                "SELL": priority.get("SELL", 3),
                "TRIM": priority.get("TRIM", 4),
                "HOLD": priority.get("HOLD", 5),
                "WAIT": priority.get("WAIT", 9),
            },
        )

    # ── 핵심 메서드 ────────────────────────────────────────

    def decide(
        self,
        ticker: str,
        analysis: AnalysisResult,
        portfolio_state: PortfolioState,
    ) -> DecisionResult:
        """
        단일 ETF에 대한 투자 결정을 생성한다.

        Args:
            ticker         : ETF 티커 (예: "KODEX 반도체", "QQQ")
            analysis       : Analysis Layer의 통합 결과
            portfolio_state: 현재 포트폴리오 전체 상태

        Returns:
            DecisionResult: 완전한 투자 결정 (action, score, reasons, warnings 포함)
        """
        # Step 1. 4개 점수 계산
        buy_score,  buy_contrib  = self._buy_calc.calculate(analysis, portfolio_state, self._config)
        hold_score, hold_contrib = self._hold_calc.calculate(analysis, portfolio_state, self._config)
        exit_score, exit_contrib = self._exit_calc.calculate(analysis, portfolio_state, self._config)
        opp_score,  opp_contrib  = self._opp_calc.calculate(analysis, portfolio_state, self._config)

        action_score = ActionScore(
            buy_score         = buy_score,
            hold_score        = hold_score,
            exit_score        = exit_score,
            opportunity_score = opp_score,
            buy_contributions  = buy_contrib,
            hold_contributions = hold_contrib,
            exit_contributions = exit_contrib,
            opp_contributions  = opp_contrib,
        )

        # Step 2. Action 결정
        action = self._matrix.determine_action(ticker, action_score, portfolio_state, self._config)

        # Step 3. 신뢰도 · 우선순위
        confidence = self._matrix.calculate_confidence(action_score)
        priority   = self._matrix.calculate_priority(action, opp_score, self._config)

        # Step 4. 비중 계산
        position = portfolio_state.positions.get(ticker)
        current_w = position.weight if position else 0.0
        target_w  = self._matrix.calculate_target_weight(
            ticker, action, action_score, portfolio_state, self._config
        )
        delta_w = target_w - current_w

        # Step 5. 리스크 레벨
        risk_level = self._matrix.determine_risk_level(action_score, analysis)

        # Step 6. 근거 & 경고
        reasons  = self._matrix.generate_reasons(action, action_score, analysis)
        warnings = self._matrix.generate_warnings(ticker, action_score, portfolio_state, analysis, self._config)

        return DecisionResult(
            ticker         = ticker,
            action         = action,
            priority       = priority,
            confidence     = confidence,
            current_weight = current_w,
            target_weight  = target_w,
            delta_weight   = delta_w,
            action_score   = action_score,
            risk_level     = risk_level,
            reasons        = reasons,
            warnings       = warnings,
            timestamp      = datetime.now(),
        )

    def decide_all(
        self,
        analyses: List[AnalysisResult],
        portfolio_state: PortfolioState,
    ) -> List[DecisionResult]:
        """
        여러 ETF를 한 번에 평가하고 priority 순으로 정렬한다.

        사용 예:
            results = engine.decide_all(analysis_list, state)
            for r in results:
                print(r.summary())
        """
        results = [
            self.decide(a.ticker, a, portfolio_state)
            for a in analyses
        ]
        # priority 오름차순, 동점 시 opportunity_score 내림차순
        results.sort(key=lambda r: (r.priority, -r.opportunity_score))
        return results

    def get_actionable(
        self, analyses: List[AnalysisResult], portfolio_state: PortfolioState
    ) -> List[DecisionResult]:
        """BUY/ADD/TRIM/SELL만 필터링해 반환"""
        return [
            r for r in self.decide_all(analyses, portfolio_state)
            if r.is_actionable
        ]

    # ── 디버그 헬퍼 ────────────────────────────────────────

    def explain(self, result: DecisionResult) -> str:
        """결정 결과를 사람이 읽기 쉬운 형태로 출력"""
        lines = [
            f"═══ {result.ticker} 투자 결정 ═══",
            f"액션   : {result.action.value}",
            f"우선순위: #{result.priority}",
            f"신뢰도 : {result.confidence:.0%}",
            f"비중   : {result.current_weight:.1%} → {result.target_weight:.1%} ({result.delta_weight:+.1%})",
            f"리스크 : {result.risk_level.value}",
            "",
            f"─── 점수 ───────────────────────────────",
            f"매수 신호  : {result.buy_score:.1f}/100",
            f"보유 신호  : {result.hold_score:.1f}/100",
            f"매도 신호  : {result.exit_score:.1f}/100",
            f"기회 점수  : {result.opportunity_score:.1f}/100",
            "",
            "─── 근거 ───────────────────────────────",
        ]
        for i, r in enumerate(result.reasons, 1):
            lines.append(f"  {i}. {r}")

        if result.warnings:
            lines.append("")
            lines.append("─── 경고 ───────────────────────────────")
            for w in result.warnings:
                lines.append(f"  ⚠ {w}")

        lines.append("")
        lines.append("─── 기여 내역 (BuyScore) ───────────────")
        for c in result.action_score.buy_contributions:
            lines.append(
                f"  {c.direction} {c.factor:20s} {c.raw_value:5.1f}pt × {c.weight:.0%} = {c.contribution:5.1f}pt  [{c.interpretation}]"
            )

        lines.append("")
        lines.append("─── 기여 내역 (ExitScore) ──────────────")
        for c in result.action_score.exit_contributions:
            lines.append(
                f"  {c.direction} {c.factor:20s} {c.raw_value:5.1f}pt × {c.weight:.0%} = {c.contribution:5.1f}pt  [{c.interpretation}]"
            )

        return "\n".join(lines)
