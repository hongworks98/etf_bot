"""
validation/backtesting/full_backtest.py
Full System Backtest — 포트폴리오 시뮬레이션
"""
from __future__ import annotations
from typing import List, Dict
from validation.data_models import (
    DecisionRecord, PriceHistory, BacktestResult, TradeRecord
)

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0


class FullBacktest:
    """
    Simulates portfolio performance by following DecisionRecord weights.
    Daily rebalancing is applied only when weights change.
    """
    REBALANCE_THRESHOLD = 0.03  # 3% drift triggers rebalance

    def run(
        self,
        records: List[DecisionRecord],
        price_history: PriceHistory,
        initial_capital: float = 100_000.0,
    ) -> BacktestResult:
        if not records or not price_history.prices:
            return self._empty(initial_capital)

        tickers   = price_history.all_tickers()
        dates     = price_history.dates
        n_dates   = len(dates)

        # Build daily return matrix
        ret_matrix: Dict[str, List[float]] = {}
        for t in tickers:
            prices = price_history.prices[t]
            ret_matrix[t] = [0.0] + [(prices[i]/prices[i-1])-1
                                      for i in range(1, len(prices))]

        # Align records to dates
        rec_by_date: Dict[str, DecisionRecord] = {r.date: r for r in records}

        port_values = [initial_capital]
        daily_rets  = []
        trades: List[TradeRecord] = []
        current_weights: Dict[str, float] = {t: 1.0/len(tickers) for t in tickers}

        for i in range(1, n_dates):
            date = dates[i]

            # Check if rebalance needed
            new_rec = rec_by_date.get(date)
            if new_rec and new_rec.weights:
                for t in tickers:
                    w_old = current_weights.get(t, 0.0)
                    w_new = new_rec.weights.get(t, 0.0)
                    if abs(w_new - w_old) > self.REBALANCE_THRESHOLD:
                        trades.append(TradeRecord(
                            date=date, ticker=t,
                            action="BUY" if w_new > w_old else "SELL",
                            weight_before=round(w_old, 4),
                            weight_after=round(w_new, 4),
                        ))
                current_weights = {t: new_rec.weights.get(t, 0.0) for t in tickers}

            # Daily portfolio return
            port_ret = sum(
                current_weights.get(t, 0.0) * ret_matrix.get(t, [0.0]*n_dates)[i]
                for t in tickers
            )
            prev_val = port_values[-1]
            port_values.append(prev_val * (1 + port_ret))
            daily_rets.append(port_ret)

        total_return = (port_values[-1] - initial_capital) / initial_capital

        # Win rate per trade (crude: based on direction correct)
        n_win = sum(1 for r in records if r.correct)
        win_rate = n_win / len(records) if records else 0.0

        return BacktestResult(
            dates           = dates[1:],
            portfolio_values= port_values[1:],
            daily_returns   = daily_rets,
            trades          = trades,
            total_return    = round(total_return, 6),
            n_trades        = len(trades),
            win_rate        = round(win_rate, 4),
            avg_hold_days   = round(n_dates / max(len(trades), 1), 1),
        )

    @staticmethod
    def _empty(capital: float) -> BacktestResult:
        return BacktestResult(
            dates=[], portfolio_values=[], daily_returns=[],
            trades=[], total_return=0.0, n_trades=0,
            win_rate=0.0, avg_hold_days=0.0,
        )
