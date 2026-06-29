"""
engines/rotation/analyzers/dashboard_builder.py
Dashboard Builder — generates 6 visualization data structures.
"""
from __future__ import annotations
from typing import Dict, List
from engines.rotation.data_models import (
    DashboardData, RotationConfig, RotationDirection, RotationResult,
)


class DashboardBuilder:
    """SRP: Builds Dashboard-ready data from RotationResult collection."""

    def _score_to_color(self, rotation_score: float, cfg: RotationConfig) -> str:
        colors = cfg.heatmap_colors
        if rotation_score >= 85:
            return colors.get("extreme",  "#8B0000")
        if rotation_score >= 65:
            return colors.get("strong",   "#E74C3C")
        if rotation_score >= 45:
            return colors.get("moderate", "#F39C12")
        if rotation_score >= 30:
            return colors.get("weak",     "#27AE60")
        return colors.get("none", "#2ECC71")

    def _flow_color(self, capital_flow_score: float, cfg: RotationConfig) -> str:
        colors = cfg.flow_colors
        if capital_flow_score >= 60:
            return colors.get("inflow",  "#1A7C4E")
        if capital_flow_score <= 40:
            return colors.get("outflow", "#C0392B")
        return colors.get("neutral", "#7F8C8D")

    def build(
        self,
        results: Dict[str, RotationResult],
        directions: List[RotationDirection],
        cfg: RotationConfig,
    ) -> DashboardData:
        dd = DashboardData()

        # 1. Rotation Heatmap — per-ETF colored cell
        dd.rotation_heatmap = [
            {
                "ticker":          r.ticker,
                "rotation_score":  round(r.rotation_score, 1),
                "stage":           r.stage.value,
                "strength":        r.strength.value,
                "conviction":      round(r.conviction_score, 1),
                "timing":          r.timing.value,
                "color":           self._score_to_color(r.rotation_score, cfg),
                "is_false":        r.is_false_rotation,
            }
            for r in sorted(results.values(), key=lambda x: x.rotation_score, reverse=True)
        ]

        # 2. Sector Flow Map — FROM→TO arrows
        dd.sector_flow_map = [
            {
                "from":       d.from_sector,
                "to":         d.to_sector,
                "strength":   d.strength.value,
                "confidence": round(d.confidence, 2),
                "score_from": round(d.rotation_score_from, 1),
                "score_to":   round(d.rotation_score_to, 1),
                "description": d.description,
            }
            for d in directions
        ]

        # 3. Rotation Network — nodes + edges for graph visualization
        nodes = [
            {
                "id":       r.ticker,
                "score":    round(r.rotation_score, 1),
                "stage":    r.stage.value,
                "color":    self._score_to_color(r.rotation_score, cfg),
                "size":     max(10, int(r.rotation_score / 5)),
            }
            for r in results.values()
        ]
        edges = [
            {
                "source":   d.from_sector,
                "target":   d.to_sector,
                "weight":   round(d.confidence, 2),
                "label":    d.strength.value,
            }
            for d in directions
        ]
        dd.rotation_network = [{"nodes": nodes, "edges": edges}]

        # 4. Capital Flow Map — volume-weighted flow per ETF
        dd.capital_flow_map = [
            {
                "ticker":      r.ticker,
                "flow_score":  round(r.capital_flow_score, 1),
                "color":       self._flow_color(r.capital_flow_score, cfg),
                "direction":   "inflow" if r.capital_flow_score >= 60 else
                               ("outflow" if r.capital_flow_score <= 40 else "neutral"),
            }
            for r in sorted(results.values(), key=lambda x: x.capital_flow_score, reverse=True)
        ]

        # 5. Rotation Timeline — score history per ETF (from attribution top factor)
        dd.rotation_timeline = [
            {
                "ticker":       r.ticker,
                "stage":        r.stage.value,
                "current_score": round(r.rotation_score, 1),
                "persistence_days": r.persistence_days,
                "persistence_weeks": r.persistence_weeks,
                "top_factors":  r.top_attribution_factors,
            }
            for r in results.values()
        ]

        # 6. Attribution Chart — stacked bar data
        dd.attribution_chart = [
            {
                "ticker": r.ticker,
                "bars": [
                    {
                        "factor": a.factor,
                        "pct":    a.pct_contribution,
                        "direction": a.direction,
                    }
                    for a in r.attribution
                ],
                "xai_summary": r.xai_summary,
            }
            for r in results.values()
        ]

        return dd
