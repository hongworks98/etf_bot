"""
engines/relative_strength/analyzers/leadership_detector.py
Leadership Detector — classifies each ETF as Leader / Follower / Laggard.
"""
from __future__ import annotations

from engines.relative_strength.data_models import LeaderStatus, RSConfig, RSRankInfo


class LeadershipDetector:
    """
    SRP: Responsible solely for leadership classification.
    Rules:
      Leader   : rs_score >= leader_rs_threshold  AND  rank in top 1/3
      Laggard  : rs_score <= laggard_rs_threshold  OR  rank in bottom 1/3
      Follower : everything else
    """

    def classify(
        self,
        rs_score: float,
        rank_info: RSRankInfo,
        config: RSConfig,
    ) -> LeaderStatus:
        total = rank_info.total_sectors or 1
        rank  = rank_info.current_rank

        top_cutoff    = max(1, round(total * config.leader_rank_top_pct))
        bottom_cutoff = min(total, round(total * config.laggard_rank_bot_pct))

        # Leader: strong RS AND in the top tier
        if rs_score >= config.leader_rs_threshold and rank <= top_cutoff:
            return LeaderStatus.LEADER

        # Laggard: weak RS OR in the bottom tier
        if rs_score <= config.laggard_rs_threshold or rank > bottom_cutoff:
            return LeaderStatus.LAGGARD

        return LeaderStatus.FOLLOWER
