"""
engines/relative_strength/analyzers/heatmap_builder.py
Heatmap Builder — converts RelativeStrengthResult list into Dashboard-ready HeatmapData.
"""
from __future__ import annotations

from typing import Dict, List

from engines.relative_strength.data_models import (
    HeatmapCell, HeatmapData, RelativeStrengthResult, RSConfig,
)


class HeatmapBuilder:
    """
    SRP: Responsible solely for building heatmap visualization data.
    Maps rs_score → hex color, assembles HeatmapCell per ETF,
    returns HeatmapData sorted by rank.
    """

    def _score_to_color(self, rs_score: float, config: RSConfig) -> str:
        colors = config.heatmap_colors
        if rs_score >= 75:
            return colors.get("excellent", "#1a7c4e")
        if rs_score >= 60:
            return colors.get("strong",    "#2ecc71")
        if rs_score >= 40:
            return colors.get("neutral",   "#f39c12")
        if rs_score >= 25:
            return colors.get("weak",      "#e74c3c")
        return colors.get("critical",      "#8e1a0e")

    def build(
        self,
        results: Dict[str, RelativeStrengthResult],
        config: RSConfig,
    ) -> HeatmapData:
        cells: List[HeatmapCell] = []

        for ticker, res in results.items():
            color = self._score_to_color(res.rs_score, config)
            cell = HeatmapCell(
                ticker=ticker,
                rs_score=round(res.rs_score, 1),
                rank=res.rank.current_rank,
                leader_status=res.leader_status.value,
                timeframe_scores=res.timeframe_dict,
                trend_direction=res.trend.direction.value,
                color_hex=color,
                rank_change=res.rank.rank_change,
                rank_jump=res.rank.rank_jump,
            )
            cells.append(cell)

        return HeatmapData(cells=cells)
