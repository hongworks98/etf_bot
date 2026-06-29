"""
engines/relative_strength/analyzers/ranking_engine.py
Ranking Engine — ranks all sector ETFs by composite RS score.
"""
from __future__ import annotations

from typing import Dict, List

from engines.relative_strength.data_models import RSConfig, RSRankInfo


class RankingEngine:
    """
    SRP: Responsible solely for assigning and comparing ranks.
    Input:  {ticker: composite_rs_score}
    Output: {ticker: RSRankInfo}
    Rank 1 = highest RS score.
    """

    def rank(
        self,
        scores: Dict[str, float],
        previous_rankings: Dict[str, int],
        config: RSConfig,
    ) -> Dict[str, RSRankInfo]:
        """
        Args:
            scores            : {ticker: composite_rs_score (0~100)}
            previous_rankings : {ticker: previous_rank}
            config            : RSConfig
        Returns:
            {ticker: RSRankInfo}
        """
        if not scores:
            return {}

        # Sort descending by score → rank 1 = best
        sorted_tickers: List[str] = sorted(scores, key=lambda t: scores[t], reverse=True)
        total = len(sorted_tickers)
        result: Dict[str, RSRankInfo] = {}

        for rank_pos, ticker in enumerate(sorted_tickers, start=1):
            prev_rank   = previous_rankings.get(ticker, rank_pos)   # default: no change
            rank_change = prev_rank - rank_pos                       # positive = improved
            rank_jump   = abs(rank_change) >= config.rank_jump_threshold

            # Percentile: rank 1 of N → ~100, rank N → ~0
            # percentile = (total - rank_pos) / (total - 1) * 100  if total > 1
            percentile = (total - rank_pos) / (total - 1) * 100.0 if total > 1 else 100.0

            result[ticker] = RSRankInfo(
                current_rank=rank_pos,
                previous_rank=prev_rank,
                rank_change=rank_change,
                rank_jump=rank_jump,
                total_sectors=total,
                percentile=round(percentile, 1),
            )

        return result

    def sorted_rankings(self, rank_infos: Dict[str, RSRankInfo]) -> List[str]:
        """Return tickers sorted by current rank (best first)."""
        return sorted(rank_infos, key=lambda t: rank_infos[t].current_rank)
