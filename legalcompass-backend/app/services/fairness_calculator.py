"""
Overall Fairness Score Calculator for LegalCompass.

Calculates an authoritative document-level fairness score [0-100] directly
from evaluated clause-level results, replacing naive arithmetic averaging
of LLM batch scores.

Key principles:
- Authoritative input: final merged Clause list.
- Differential weighting: High-risk clauses carry high impact (3.0x),
  while neutral/definitional clauses have low influence (0.5x).
- Severity adjustment: Severe traps (uncapped indemnity, unconditional IP transfer)
  cannot be mathematically masked by dozens of boilerplate definitions.
- Batch invariance: The calculated score is deterministic and invariant to
  how many batches were used during LLM processing.
"""

from typing import List
from app.schemas.contract import Clause


# Tunable constants for material risk weights
WEIGHT_NEUTRAL = 0.5   # Pure definitions and headings have minimal influence
WEIGHT_LOW = 1.0       # Standard commercial covenants
WEIGHT_MEDIUM = 1.8    # Significant imbalance (Net-60, subjective withholding)
WEIGHT_HIGH = 3.0      # Existential legal traps (uncapped indemnity, IP loss)


def calculate_overall_fairness(clauses: List[Clause]) -> int:
    """Calculates deterministic overall fairness score [10-100] from final clauses."""
    if not clauses:
        return 50

    total_weighted_fairness = 0.0
    total_weight = 0.0
    high_count = 0
    medium_count = 0

    for c in clauses:
        risk = (c.risk_level or "LOW").upper()
        unfairness = c.unfairness_score if c.unfairness_score is not None else 25

        # Determine clause weight
        if risk == "HIGH":
            weight = WEIGHT_HIGH
            high_count += 1
        elif risk == "MEDIUM":
            weight = WEIGHT_MEDIUM
            medium_count += 1
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
