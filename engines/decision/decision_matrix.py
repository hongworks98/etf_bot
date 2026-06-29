"""
engines/decision/decision_matrix.py
DecisionMatrix — 4개 점수를 받아 최종 Action을 결정

규칙 우선순위 (낮은 번호 = 먼저 적용):
  1. [리스크 오버라이드] exit_score > 85 → SELL
  2. [리스크 오버라이드] exit_score > 70 + 보유 중 → TRIM
  3. [신규 강력 매수]   buy_score > 75 + 미보유 + 현금 충분 + 국면 1~2위 → BUY
  4. [신규 일반 매수]   buy_score > 60 + 미보유 + exit_score < 40 → BUY
  5. [추가 매수]        buy_score > 55 + 보유 중 + exit_score < 40 → ADD
  6. [보유 유지]        hold_score > 45 + exit_score < 60 → HOLD
  7. [부분 매도]        exit_score > 60 + 보유 중 → TRIM
  8. [전량 매도]        exit_score > 75 + 보유 중 → SELL
  9. [기본]            → WAIT
"""

from __future__ import annotations
import statistics
from typing import List, Tuple

from engines.decision.data_models import (
    Action,
    ActionScore,
    AnalysisResult,
    DecisionConfig,
    PortfolioState,
    RiskLevel,
)


class DecisionMatrix:
    """
    4개 점수(buy/hold/exit/opportunity) + 포트폴리오 상태 → Action 결정

    이 클래스는 규칙만 담는다.
    점수 계산은 Calculator가, 오케스트레이션은 Engine이 담당.
    """

    def determine_action(
        self,
        ticker: str,
        scores: ActionScore,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> Action:
        """
        우선순위 규칙 체인으로 Action을 결정한다.
        먼저 매칭되는 규칙이 적용된다.
        """
        thresholds = config.thresholds
        position = state.positions.get(ticker)
        is_held = position is not None
        current_w = position.weight if is_held else 0.0

        buy  = scores.buy_score
        hold = scores.hold_score
        exit_ = scores.exit_score
        opp  = scores.opportunity_score

        # ── 리스크 오버라이드 (무조건 우선) ─────────────
        if exit_ >= thresholds.risk_override_sell:
            return Action.SELL

        if exit_ >= thresholds.risk_override_trim and is_held:
            return Action.TRIM

        # ── 포트폴리오 수용 가능성 체크 ─────────────────
        can_add_position = (
            len(state.positions) < config.max_portfolio_positions
            and state.cash_pct >= config.min_cash_pct
        )

        # ── 신규 강력 매수 ───────────────────────────────
        if (not is_held
                and buy >= thresholds.strong_buy
                and exit_ < 40
                and opp >= 65
                and can_add_position):
            return Action.BUY

        # ── 신규 일반 매수 ───────────────────────────────
        if (not is_held
                and buy >= thresholds.buy
                and exit_ < 40
                and can_add_position):
            return Action.BUY

        # ── 추가 매수 ────────────────────────────────────
        if (is_held
                and buy >= thresholds.add
                and exit_ < 40
                and current_w < config.max_position_size - 0.02):
            return Action.ADD

        # ── 보유 유지 ────────────────────────────────────
        if is_held and hold >= thresholds.hold_min and exit_ < thresholds.trim:
            return Action.HOLD

        # ── 전량 매도 ────────────────────────────────────
        if is_held and exit_ >= thresholds.sell:
            return Action.SELL

        # ── 부분 매도 ────────────────────────────────────
        if is_held and exit_ >= thresholds.trim:
            return Action.TRIM

        # ── 기본: 관망 ───────────────────────────────────
        return Action.WAIT

    def calculate_confidence(self, scores: ActionScore) -> float:
        """
        신호 신뢰도 — 4개 점수의 일치도로 측정
        표준편차가 낮을수록 신호가 일관됨 → 신뢰도 높음
        """
        values = [
            scores.buy_score,
            scores.hold_score,
            100.0 - scores.exit_score,  # exit는 역방향이므로 반전
            scores.opportunity_score,
        ]
        try:
            std = statistics.stdev(values)
        except statistics.StatisticsError:
            return 0.75  # 데이터 부족 시 기본값

        # std가 낮을수록 confidence 높음 (선형 보간)
        max_std = 30.0
        min_std = 5.0
        std_clamped = max(min_std, min(max_std, std))
        confidence = 1.0 - (std_clamped - min_std) / (max_std - min_std) * 0.5
        return round(confidence, 3)

    def calculate_target_weight(
        self,
        ticker: str,
        action: Action,
        scores: ActionScore,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> float:
        """
        Action에 따른 목표 비중을 결정한다.

        BUY  → default_position_size (opportunity_score가 높으면 +α)
        ADD  → current_weight + default/2
        HOLD → current_weight (유지)
        TRIM → current_weight / 2 (절반 매도)
        SELL → 0.0
        WAIT → 0.0
        """
        position = state.positions.get(ticker)
        current_w = position.weight if position else 0.0
        default_w = config.default_position_size
        max_w = config.max_position_size

        if action == Action.BUY:
            # opportunity_score가 80 이상이면 +5%p 추가
            bonus = 0.05 if scores.opportunity_score >= 80 else 0.0
            return min(default_w + bonus, max_w)

        elif action == Action.ADD:
            return min(current_w + default_w * 0.5, max_w)

        elif action == Action.HOLD:
            return current_w

        elif action == Action.TRIM:
            return max(current_w * 0.5, config.min_position_size)

        elif action == Action.SELL:
            return 0.0

        else:  # WAIT
            return 0.0

    def calculate_priority(
        self,
        action: Action,
        opportunity_score: float,
        config: DecisionConfig,
    ) -> int:
        """
        동일 Action 내에서 opportunity_score로 세부 순위 조정.
        기본 priority는 YAML 기준, opp 점수로 ±1 미세 조정.
        """
        base = config.priority_map.get(action.value, 9)
        if action in (Action.BUY, Action.ADD):
            if opportunity_score >= 80:
                return max(1, base - 1)
            elif opportunity_score < 50:
                return base + 1
        return base

    def determine_risk_level(
        self,
        scores: ActionScore,
        analysis: AnalysisResult,
    ) -> RiskLevel:
        """
        리스크 수준 결정
        exit_score와 risk_score를 종합해 4단계로 분류
        """
        exit_ = scores.exit_score
        risk  = analysis.risk_score

        if exit_ >= 75 or risk < 25:
            return RiskLevel.RED
        elif exit_ >= 55 or risk < 45:
            return RiskLevel.ORANGE
        elif exit_ >= 35 or risk < 60:
            return RiskLevel.YELLOW
        else:
            return RiskLevel.GREEN

    def generate_reasons(
        self,
        action: Action,
        scores: ActionScore,
        analysis: AnalysisResult,
    ) -> List[str]:
        """결정 근거 3~5개를 자연어로 생성"""
        reasons = []

        # 핵심 점수 요약
        reasons.append(
            f"매크로 점수 {analysis.macro_score:.0f}/100 "
            f"({analysis.macro_state}, {analysis.macro_direction})"
        )
        reasons.append(
            f"ETF 품질 점수 {analysis.etf_score:.0f}/100 "
            f"— 트렌드 {analysis.trend_score:.0f} · RS {analysis.rs_score:.0f}"
        )

        # Action별 주요 이유
        if action == Action.BUY:
            reasons.append(f"매수 신호 {scores.buy_score:.0f}/100 — 진입 기준 충족")
            if analysis.sector_rank <= 2:
                reasons.append(f"현재 국면 섹터 순위 {analysis.sector_rank}위 — 최적 국면 진입")
        elif action == Action.ADD:
            reasons.append(f"추가 매수 신호 {scores.buy_score:.0f}/100 — 기존 포지션 강화")
        elif action == Action.HOLD:
            reasons.append(f"보유 유지 신호 {scores.hold_score:.0f}/100 — 매도 이유 없음")
        elif action == Action.TRIM:
            reasons.append(f"매도 신호 {scores.exit_score:.0f}/100 — 부분 차익 실현")
        elif action == Action.SELL:
            reasons.append(f"매도 신호 {scores.exit_score:.0f}/100 — 전량 청산")
        elif action == Action.WAIT:
            reasons.append(f"매수 신호 {scores.buy_score:.0f}/100 — 진입 기준 미달")

        # 기회 점수
        reasons.append(f"기회 점수 {scores.opportunity_score:.0f}/100")

        return reasons[:5]  # 최대 5개

    def generate_warnings(
        self,
        ticker: str,
        scores: ActionScore,
        state: PortfolioState,
        analysis: AnalysisResult,
        config: DecisionConfig,
    ) -> List[str]:
        """주의사항 (조건 해당 시만 추가)"""
        warnings = []
        position = state.positions.get(ticker)

        # 신뢰도 낮음
        confidence = self.calculate_confidence(scores)
        if confidence < 0.65:
            warnings.append(
                f"신뢰도 {confidence:.0%} — 신호 혼재, 소액 진입 권장"
            )

        # 현금 부족
        if state.cash_pct < config.min_cash_pct + 0.05:
            warnings.append(
                f"현금 {state.cash_pct:.0%} — 유동성 주의, 비중 조절 필요"
            )

        # 포트폴리오 만석
        if len(state.positions) >= config.max_portfolio_positions:
            warnings.append(
                f"보유 종목 {len(state.positions)}개 — 최대치, 기존 종목 정리 후 진입"
            )

        # 섹터 집중 경고
        if position:
            sector = position.sector or ""
            sector_exp = state.sector_exposure.get(sector, 0.0)
            if sector_exp > config.max_sector_exposure - 0.05:
                warnings.append(
                    f"섹터 노출 {sector_exp:.0%} — 섹터 집중도 임계치 접근"
                )

        # 포트폴리오 베타 과열
        if state.risk_metrics.portfolio_beta > 1.5:
            warnings.append(
                f"포트폴리오 베타 {state.risk_metrics.portfolio_beta:.2f} — 시장 민감도 과열"
            )

        return warnings[:3]  # 최대 3개
