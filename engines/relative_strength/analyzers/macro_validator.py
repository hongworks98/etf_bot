"""
engines/relative_strength/analyzers/macro_validator.py
Macro Validator — aligns current RS leadership with macro regime expectations.
"""
from __future__ import annotations

from typing import List

from engines.relative_strength.data_models import (
    LeaderStatus, MacroValidation, RSConfig,
)


class MacroValidator:
    """
    SRP: Responsible solely for macro-RS alignment validation.
    Checks whether the ETF's current leadership role is consistent
    with what the macro regime would predict.
    """

    def validate(
        self,
        ticker: str,
        leader_status: LeaderStatus,
        macro_state: str,
        config: RSConfig,
    ) -> MacroValidation:
        expected_leaders: List[str] = config.macro_expected_leaders.get(macro_state, [])
        is_expected = ticker in expected_leaders
        is_leading  = leader_status == LeaderStatus.LEADER

        actual_position = (
            "Leading"  if leader_status == LeaderStatus.LEADER  else
            "Lagging"  if leader_status == LeaderStatus.LAGGARD else
            "Neutral"
        )

        # Determine alignment key
        if is_expected and is_leading:
            key         = "expected_and_leading"
            is_aligned  = True
            description = (
                f"{ticker} is leading as expected in {macro_state} phase. "
                "Strong macro-RS alignment."
            )
            warning = None
        elif is_expected and not is_leading:
            key         = "expected_not_leading"
            is_aligned  = False
            description = (
                f"{ticker} is expected to lead in {macro_state} phase "
                "but is currently not showing leadership."
            )
            warning = f"{ticker} expected to lead but lagging — watch for catch-up or regime shift"
        elif not is_expected and is_leading:
            key         = "unexpected_leading"
            is_aligned  = False
            description = (
                f"{ticker} is leading but is NOT typical for {macro_state} phase. "
                "Possible regime mis-read or rotation precursor."
            )
            warning = f"{ticker} leading unexpectedly — verify macro state or watch for reversal"
        else:
            key         = "unexpected_not_leading"
            is_aligned  = True
            description = (
                f"{ticker} is not expected to lead in {macro_state} phase "
                "and is indeed not leading. Normal behaviour."
            )
            warning = None

        alignment_score = config.macro_alignment_scores.get(key, 50.0)

        return MacroValidation(
            is_aligned=is_aligned,
            alignment_score=alignment_score,
            expected_leaders=expected_leaders,
            actual_position=actual_position,
            description=description,
            warning=warning,
        )
