"""
engines/rotation/analyzers/rotation_attribution.py
Rotation Attribution Analyzer — XAI decomposition of the rotation signal.
"""
from __future__ import annotations
from typing import List, Tuple
from engines.rotation.data_models import RotationAttribution, RotationConfig


class RotationAttributionAnalyzer:
    """
    SRP: Responsible solely for building the XAI attribution breakdown.
    Input: raw per-factor contributions from RotationScoreCalculator.
    Output: sorted List[RotationAttribution] + one-sentence XAI summary.
    """

    def analyze(
        self,
        attributions: List[RotationAttribution],
        rotation_score: float,
        cfg: RotationConfig,
    ) -> Tuple[List[RotationAttribution], str, List[dict]]:
        """
        Returns:
            sorted_attributions : sorted by pct_contribution desc
            xai_summary         : human-readable one-sentence summary
            chart_data          : stacked bar data for Dashboard
        """
        if not attributions:
            return [], "No attribution data available.", []

        total_score = sum(a.score_contribution for a in attributions) or 1.0

        # Recompute pct to ensure sums to 100%
        for a in attributions:
            a.pct_contribution = round(a.score_contribution / total_score * 100.0, 1)

        sorted_attr = sorted(attributions, key=lambda a: a.pct_contribution, reverse=True)

        # Build XAI summary
        top2 = sorted_attr[:2]
        top2_names = " and ".join(f.factor for f in top2)
        top2_pct   = sum(f.pct_contribution for f in top2)
        xai_summary = (
            f"This rotation signal is primarily explained by {top2_names}, "
            f"which together account for {top2_pct:.0f}% of the total signal. "
            f"(Overall Rotation Score = {rotation_score:.1f})"
        )

        # Dashboard stacked bar data
        chart_data = [
            {
                "factor": a.factor,
                "contribution": a.score_contribution,
                "pct": a.pct_contribution,
                "direction": a.direction,
            }
            for a in sorted_attr
        ]

        return sorted_attr, xai_summary, chart_data

    def build_triggers(
        self,
        sorted_attributions: List[RotationAttribution],
        macro_state: str,
        breadth_health: str,
    ) -> List[str]:
        """Build human-readable rotation trigger list."""
        triggers = []
        for attr in sorted_attributions[:3]:
            if attr.pct_contribution >= 15.0:
                triggers.append(
                    f"{attr.direction} {attr.factor}: {attr.pct_contribution:.0f}% of signal"
                )
        if macro_state not in ("Unknown", ""):
            triggers.append(f"Macro regime: {macro_state}")
        if breadth_health in ("Excellent", "Healthy"):
            triggers.append(f"Broad market health: {breadth_health}")
        return triggers
