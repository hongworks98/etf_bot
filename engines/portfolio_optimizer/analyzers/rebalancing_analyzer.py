"""
engines/portfolio_optimizer/analyzers/rebalancing_analyzer.py
Determines rebalancing urgency and opportunity cost.
"""
from __future__ import annotations
from typing import Dict, List

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import (
    OptimizationConfig, RebalanceSignal, RebalanceUrgency,
    SuggestedTrade, TradeDirection,
)


class RebalancingAnalyzer(AbstractOptimizationCalculator):

    def analyze(
        self,
        current: Dict[str, float],
        target: Dict[str, float],
        portfolio_value: float,
        price_history: Dict[str, List[float]],
        cfg: OptimizationConfig,
    ) -> tuple[RebalanceSignal, List[SuggestedTrade]]:
        all_tickers = set(current) | set(target)
        deltas = {
            t: target.get(t, 0.0) - current.get(t, 0.0)
            for t in all_tickers
        }
        abs_deltas = {t: abs(d) for t, d in deltas.items()}
        max_delta     = max(abs_deltas.values(), default=0.0)
        total_turnover = sum(abs_deltas.values()) / 2  # one-way turnover

        # Urgency
        if max_delta >= cfg.immediate_threshold:
            urgency = RebalanceUrgency.IMMEDIATE
            reason  = f"최대 이탈 {max_delta:.1%} ≥ {cfg.immediate_threshold:.0%} — 즉시 리밸런싱 필요"
        elif max_delta >= cfg.this_week_threshold:
            urgency = RebalanceUrgency.THIS_WEEK
            reason  = f"최대 이탈 {max_delta:.1%} ≥ {cfg.this_week_threshold:.0%} — 이번 주 리밸런싱 권고"
        elif max_delta >= cfg.this_month_threshold:
            urgency = RebalanceUrgency.THIS_MONTH
            reason  = f"최대 이탈 {max_delta:.1%} ≥ {cfg.this_month_threshold:.0%} — 이번 달 내 리밸런싱"
        elif max_delta > 0.001:
            urgency = RebalanceUrgency.MONITOR
            reason  = f"이탈 {max_delta:.1%} — 모니터링 유지"
        else:
            urgency = RebalanceUrgency.NO_ACTION
            reason  = "리밸런싱 불필요"

        # Costs & opportunity
        est_cost = total_turnover * portfolio_value * cfg.transaction_cost_pct * 2
        opp_cost_daily   = cfg.daily_alpha_estimate * portfolio_value
        opp_cost_monthly = opp_cost_daily * 21

        days_to_breakeven = (
            int(est_cost / opp_cost_daily) + 1
            if opp_cost_daily > 0 else 0
        )

        signal = RebalanceSignal(
            urgency=urgency,
            max_delta=round(max_delta, 4),
            total_turnover=round(total_turnover, 4),
            estimated_cost=round(est_cost, 2),
            opportunity_cost_daily=round(opp_cost_daily, 2),
            opportunity_cost_monthly=round(opp_cost_monthly, 2),
            days_to_breakeven=days_to_breakeven,
            reason=reason,
        )

        # Suggested trades
        trades: List[SuggestedTrade] = []
        for t in sorted(all_tickers, key=lambda x: abs(deltas[x]), reverse=True):
            d = deltas[t]
            if abs(d) < cfg.rebalance_threshold:
                continue
            trade_val = abs(d) * portfolio_value
            if trade_val < cfg.min_trade_value:
                continue
            prices = price_history.get(t, [])
            price  = prices[-1] if prices else cfg.price_fallback
            shares = trade_val / max(price, 0.01)
            direction = TradeDirection.BUY if d > 0 else TradeDirection.SELL
            trades.append(SuggestedTrade(
                ticker=t,
                direction=direction,
                current_weight=round(current.get(t, 0.0), 4),
                target_weight=round(target.get(t, 0.0), 4),
                delta_weight=round(d, 4),
                trade_value=round(trade_val, 2),
                shares_estimate=round(shares, 2),
                reason=f"{direction.value} {abs(d):.1%} ({trade_val:,.0f}$)",
            ))
        return signal, trades
