"""
Overall Fairness Score Calculator for LegalCompass — Accuracy V2.

Calculates an authoritative document-level fairness score [0-100] directly
from evaluated clause-level results, with risk-bearing awareness.

Key principles:
- Authoritative input: final merged Clause list.
- Risk-bearing awareness: Non-risk-bearing clauses (definitions, headings,
  recitals) have near-zero influence (0.2x weight), preventing them from
  mathematically masking predatory traps.
- Differential weighting: High-risk clauses carry high impact (3.0x),
  while standard LOW clauses have moderate influence (1.0x).
- Severity adjustment: Only risk-bearing HIGH/MEDIUM clauses count toward
  severity penalties.
- Batch invariance: The calculated score is deterministic and invariant to
  how many batches were used during LLM processing.
"""

from typing import List
from app.schemas.contract import Clause


# Tunable constants for material risk weights
WEIGHT_NON_RISK = 0.2  # Non-risk-bearing clauses (definitions, headings, recitals)
WEIGHT_NEUTRAL = 0.5   # Risk-bearing but neutral clauses
WEIGHT_LOW = 1.0       # Standard commercial covenants
WEIGHT_MEDIUM = 1.8    # Significant imbalance (Net-60, subjective withholding)
WEIGHT_HIGH = 3.0      # Existential legal traps (uncapped indemnity, IP loss)


def calculate_overall_fairness(clauses: List[Clause]) -> int:
    """Calculates deterministic overall fairness score [10-100] from final clauses.

    Accuracy V2: Uses is_risk_bearing to ensure non-operative clauses
    (definitions, headings, recitals) don't dilute the score.
    """
    if not clauses:
        return 50

    total_weighted_fairness = 0.0
    total_weight = 0.0
    high_count = 0
    medium_count = 0

    for c in clauses:
        risk = (c.risk_level or "LOW").upper()
        unfairness = c.unfairness_score if c.unfairness_score is not None else 25
        is_risk_bearing = getattr(c, "is_risk_bearing", True)

        # Accuracy V2: Non-risk-bearing clauses get near-zero weight
        if not is_risk_bearing:
            weight = WEIGHT_NON_RISK
        elif risk == "HIGH":
            weight = WEIGHT_HIGH
            high_count += 1  # Only count risk-bearing HIGH clauses
        elif risk == "MEDIUM":
            weight = WEIGHT_MEDIUM
            medium_count += 1  # Only count risk-bearing MEDIUM clauses
        elif risk == "NEUTRAL":
            weight = WEIGHT_NEUTRAL
        else:  # LOW or other
            weight = WEIGHT_LOW

        # Clause fairness is inverted unfairness (0 unfair -> 100 fair)
        clause_fairness = max(0, min(100, 100 - unfairness))
        total_weighted_fairness += clause_fairness * weight
        total_weight += weight

    if total_weight <= 0:
        return 50

    weighted_avg = total_weighted_fairness / total_weight

    # Structural severity penalty for material traps
    # Prevents contracts with 20 boilerplate definitions from hiding 2 fatal traps
    # Only applies to risk-bearing HIGH clauses
    if high_count == 1:
        severity_penalty = 8
    elif high_count == 2:
        severity_penalty = 16
    elif high_count >= 3:
        severity_penalty = 16 + (high_count - 2) * 5
    else:
        severity_penalty = 0

    final_score = round(weighted_avg - severity_penalty)
    return max(10, min(100, final_score))
