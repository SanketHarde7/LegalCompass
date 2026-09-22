"""
Heuristic Legal Rule Engine for LegalCompass.

Performs lightweight structural and semantic analysis of contract clauses.
Replaces shallow keyword blacklist matching with:
- Directionality (who is bound vs. who benefits)
- Reciprocity detection (mutual vs. unilateral)
- Negation handling ("shall not indemnify", "no liability")
- Conditionality (payment-conditioned IP transfer)
- Definitions detection (pure definitions without asymmetric covenants remain NEUTRAL/LOW)
"""

import re
from typing import NamedTuple, Optional, List


class HeuristicAssessment(NamedTuple):
    category: str
    risk_level: str  # "HIGH", "MEDIUM", "LOW", "NEUTRAL"
    unfairness_score: int  # 0 - 100
    plain_summary: str
    suggested_pushback: Optional[str]


class HeuristicEngine:
    """Deterministic structural and semantic legal evaluator."""

    # Negation indicators
    RE_NEGATION = re.compile(
        r"\b(?:shall\s+not|will\s+not|may\s+not|is\s+not\s+required\s+to|have\s+no|has\s+no|"
        r"under\s+no\s+circumstances|neither\s+party\s+shall|no\s+(?:indemnification|liability|obligation)|"
        r"shall\s+not\s+be\s+liable|not\s+be\s+responsible|waives?\s+all\s+claims|is\s+under\s+no\s+duty)\b",
        re.IGNORECASE,
    )

    # Reciprocal / bilateral indicators
    RE_RECIPROCAL = re.compile(
        r"\b(?:each\s+party|both\s+parties|mutually|mutual|either\s+party|reciprocal|reciprocally|"
        r"neither\s+party|solely\s+to\s+the\s+extent\s+caused\s+by|each\s+shall)\b",
        re.IGNORECASE,
    )

    # Pure definition indicators
    RE_DEFINITION = re.compile(
        r'^(?:["\']([^"\']+)["\']\s+(?:means|shall\s+mean|refers\s+to|includes?)|'
        r'(?:Section\s+\d+|Clause\s+\d+|\d+\.\d+)?\s*["\']([^"\']+)["\']\s+(?:means|shall\s+mean)|'
        r'definitions?\s*[-—:])',
        re.IGNORECASE,
    )

    def evaluate_clause(self, title: str, text: str) -> HeuristicAssessment:
        """Evaluates clause text using structural and directional legal rules."""
        full_text = f"{title}\n{text}".strip()
        text_lower = full_text.lower()
        body_lower = text.lower()

        # 1. Pure Definitional Sentence Check
        # If it only defines a term and contains no substantive asymmetric duty
        if self._is_pure_definition(title, text):
            return HeuristicAssessment(
                category="OTHER",
                risk_level="NEUTRAL",
                unfairness_score=10,
                plain_summary="Definitional provision defining contract terminology without imposing asymmetric legal exposure.",
                suggested_pushback=None,
            )

        # 2. Negation Check: Does the clause explicitly disclaim or negate liability/duty?
        is_negated = bool(self.RE_NEGATION.search(body_lower))
        is_reciprocal = bool(self.RE_RECIPROCAL.search(body_lower))

        # Explicit disclaimer of contractor duty (e.g. "Contractor shall have no indemnification obligation")
        if is_negated:
            if any(k in body_lower for k in ["no indemn", "shall not indemnify", "not be required to indemnify"]):
                return HeuristicAssessment(
                    category="INDEMNIFICATION",
                    risk_level="LOW",
                    unfairness_score=15,
                    plain_summary="Explicitly relieves contractor from indemnification duties, presenting zero unilateral liability exposure.",
                    suggested_pushback=None,
                )
            if any(k in body_lower for k in ["neither party shall", "neither party may terminate without cause"]):
                return HeuristicAssessment(
                    category="TERMINATION" if "terminate" in body_lower else "OTHER",
                    risk_level="LOW",
                    unfairness_score=20,
                    plain_summary="Bilateral negative covenant prohibiting both parties from taking adverse unilateral action.",
                    suggested_pushback=None,
                )
            if any(k in body_lower for k in ["shall not be liable", "no liability"]):
                if is_reciprocal:
                    return HeuristicAssessment(
                        category="LIABILITY",
                        risk_level="LOW",
                        unfairness_score=20,
                        plain_summary="Mutual disclaimer of indirect or consequential damages, standard in commercial agreements.",
                        suggested_pushback=None,
                    )

        # 3. Indemnification Evaluation
        if any(k in text_lower for k in ["indemn", "hold harmless", "defend and hold"]):
            return self._evaluate_indemnification(body_lower, is_reciprocal, is_negated)

        # 4. Intellectual Property & Work Product Evaluation
        if any(k in text_lower for k in ["intellectual property", "inventions", "work made for hire", "assigns", "deliverables"]):
            return self._evaluate_ip(title, body_lower)

        # 5. Termination Evaluation
        if any(k in text_lower for k in ["terminate", "termination", "cancel", "renewal"]):
            return self._evaluate_termination(body_lower, is_reciprocal, is_negated)

        # 6. Payment Terms & Setoff
        if any(k in text_lower for k in ["payment", "invoice", "net 60", "net 90", "net-60", "net-90", "withhold", "setoff", "set off"]):
            return self._evaluate_payment(body_lower)

        # 7. Tenancy / Quiet Enjoyment
        if any(k in text_lower for k in ["enter premises", "unannounced", "routine inspection", "carpet", "deposit"]):
            return self._evaluate_tenancy(body_lower)

        # 8. Order of Precedence Conflict
        if any(k in text_lower for k in ["order of precedence", "purchase order shall control", "invoice shall control", "supersede"]):
            if any(k in body_lower for k in ["purchase order", "invoice", "vendor form"]) and any(k in body_lower for k in ["control", "prevail", "supersede"]):
                return HeuristicAssessment(
                    category="DISPUTE_RESOLUTION",
                    risk_level="HIGH",
                    unfairness_score=85,
                    plain_summary="Order of precedence carves out payment terms or liability to purchase orders, allowing unilateral counterparty terms to override this agreement.",
                    suggested_pushback="The terms and conditions of this Agreement shall strictly prevail and control over any conflict with any Purchase Order or invoice.",
                )

        # 9. Default Standard Provision
        category = "DISPUTE_RESOLUTION" if any(k in text_lower for k in ["dispute", "governing law", "jurisdiction"]) else "OTHER"
        return HeuristicAssessment(
            category=category,
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard commercial provision with customary obligations.",
            suggested_pushback=None,
        )

    def _is_pure_definition(self, title: str, text: str) -> bool:
        """Determines if a clause is purely a definitional entry naming a term."""
        title_lower = title.lower()
        is_def_title = "definitions —" in title_lower or "definitions" in title_lower
        has_quote = bool(re.match(r'^\s*(?:\d+\.\d+\s+)?["\']([^"\']+)["\']\s+(?:means|shall\s+mean|refers\s+to|includes)', text, re.IGNORECASE))

        if is_def_title or has_quote:
            # Dangerous operative covenant patterns that disguise substantive traps in definitions
            operative_trap_patterns = [
                r"\b(?:contractor|tenant|client|party)\s+(?:shall|must|hereby\s+agrees\s+to)\s+(?:indemnify|defend|hold\s+harmless)\b",
                r"\bhereby\s+(?:irrevocably\s+)?assigns\b",
                r"\b(?:shall|will)\s+forfeit\b",
                r"\buncapped\s+liability\b",
            ]
            if not any(re.search(p, text, re.IGNORECASE) for p in operative_trap_patterns):
                return True
        return False

    def _evaluate_indemnification(self, body_lower: str, is_reciprocal: bool, is_negated: bool) -> HeuristicAssessment:
        if is_negated:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="LOW",
                unfairness_score=15,
                plain_summary="Explicitly negates indemnification duties for the contractor.",
                suggested_pushback=None,
            )

        if is_reciprocal:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="LOW",
                unfairness_score=30,
                plain_summary="Bilateral mutual indemnification provision where each party is responsible solely for its own breach or negligence.",
                suggested_pushback=None,
            )

        # Unilateral indemnification
        is_uncapped = any(k in body_lower for k in ["uncapped", "unlimited", "any and all", "without limitation", "all losses", "defense costs", "attorney fees"])
        has_liability_cap = any(k in body_lower for k in ["subject to the liability cap", "capped at", "limited to fees"])

        if is_uncapped and not has_liability_cap:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="HIGH",
                unfairness_score=92,
                plain_summary="Imposes uncapped unilateral indemnification on you, exposing you to personal legal defense bills and third-party liabilities if the counterparty is sued.",
                suggested_pushback="Each party shall mutually indemnify the other against third-party claims arising solely from its gross negligence. Total liability under this indemnity shall be capped at fees received under this Agreement.",
            )
        else:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="MEDIUM",
                unfairness_score=60,
                plain_summary="Unilateral indemnification duty requiring you to cover counterparty losses, though subject to general legal limits.",
                suggested_pushback="Indemnification obligations shall be mutual, fault-based, and capped at total fees paid under this Agreement.",
            )

    def _evaluate_ip(self, title: str, body_lower: str) -> HeuristicAssessment:
        # Check if it is a pre-existing IP / Background IP carve-out or definition
        if "background ip" in title.lower() or "pre-existing" in body_lower:
            return HeuristicAssessment(
                category="INTELLECTUAL_PROPERTY",
                risk_level="LOW",
                unfairness_score=20,
                plain_summary="Recognizes contractor retention of pre-existing background IP and developer tooling.",
                suggested_pushback=None,
            )

        has_assignment = any(k in body_lower for k in ["assigns", "transfers", "work made for hire", "irrevocably assign", "exclusive property of client"])
        is_conditioned_on_payment = any(k in body_lower for k in ["upon full payment", "receipt of full payment", "conditioned upon payment", "cleared funds", "subject to payment"])
        is_unconditional = any(k in body_lower for k in ["immediately upon creation", "irrespective of whether client has paid", "regardless of payment", "upon inception"])

        if has_assignment:
            if is_unconditional or (not is_conditioned_on_payment and any(k in body_lower for k in ["irrevocably", "without cap", "immediate"])):
                return HeuristicAssessment(
                    category="INTELLECTUAL_PROPERTY",
                    risk_level="HIGH",
                    unfairness_score=88,
                    plain_summary="Ownership of all code, designs, and deliverables transfers immediately upon creation, meaning the client owns your work product even if they fail to pay your invoice.",
                    suggested_pushback="All intellectual property rights in and to Deliverables shall transfer exclusively to Client strictly upon Contractor's receipt of full and complete invoice payment.",
                )
            elif is_conditioned_on_payment:
                return HeuristicAssessment(
                    category="INTELLECTUAL_PROPERTY",
                    risk_level="LOW",
                    unfairness_score=25,
                    plain_summary="Standard, balanced IP assignment provision where ownership transfer is strictly conditioned upon receipt of full payment.",
                    suggested_pushback=None,
                )
            else:
                return HeuristicAssessment(
                    category="INTELLECTUAL_PROPERTY",
                    risk_level="MEDIUM",
                    unfairness_score=55,
                    plain_summary="Transfers intellectual property rights without explicit language conditioning the transfer on cleared payment.",
                    suggested_pushback="Title and copyright to Deliverables shall pass to Client upon receipt of full payment for the applicable milestone.",
                )

        return HeuristicAssessment(
            category="INTELLECTUAL_PROPERTY",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard intellectual property provision outlining scope and licensing.",
            suggested_pushback=None,
        )

    def _evaluate_termination(self, body_lower: str, is_reciprocal: bool, is_negated: bool) -> HeuristicAssessment:
        if is_negated:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="LOW",
                unfairness_score=20,
                plain_summary="Bilateral restriction preventing termination without cause.",
                suggested_pushback=None,
            )

        # Unilateral immediate termination for convenience with forfeiture
        unilateral_kill = any(k in body_lower for k in ["client may terminate at any time", "terminate without cause at will", "forfeit unbilled", "without notice or penalty", "terminate immediately at its sole option"])
        has_forfeiture = any(k in body_lower for k in ["without payment for work", "forfeit", "no compensation"])

        if unilateral_kill or has_forfeiture:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="HIGH",
                unfairness_score=85,
                plain_summary="Allows the client to terminate the contract at will without adequate notice and withhold compensation for in-progress work.",
                suggested_pushback="Either party may terminate for convenience upon thirty (30) days prior written notice. Upon termination, Client shall pay Contractor for all completed work and non-cancelable commitments.",
            )

        if is_reciprocal or any(k in body_lower for k in ["either party may terminate upon", "both parties"]):
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="LOW",
                unfairness_score=25,
                plain_summary="Mutual termination clause allowing either party to end the engagement with customary prior written notice.",
                suggested_pushback=None,
            )

        return HeuristicAssessment(
            category="TERMINATION",
            risk_level="MEDIUM",
            unfairness_score=50,
            plain_summary="Termination provision with moderate notice or unilateral cure requirements.",
            suggested_pushback="Provide mutual termination rights with 30 days written notice and compensation for work completed to date.",
        )

    def _evaluate_payment(self, body_lower: str) -> HeuristicAssessment:
        # Severe payment delay or unilateral withholding
        is_delayed = any(k in body_lower for k in ["net 60", "net-60", "net 90", "net-90", "net 120", "within 90 days"])
        has_discretionary_withholding = any(k in body_lower for k in ["sole discretion", "arbitrarily withhold", "disputed portion", "withhold payment without interest", "setoff", "set off"])

        if is_delayed or has_discretionary_withholding:
            return HeuristicAssessment(
                category="PAYMENT_TERMS",
                risk_level="MEDIUM",
                unfairness_score=65,
                plain_summary="Imposes delayed payment cycles (Net-60/Net-90) or subjective invoice withholding rights that expose contractor to cash flow vulnerability.",
                suggested_pushback="Invoices shall be payable within thirty (30) days of receipt. Undisputed invoice portions shall be disbursed immediately, and disputed items resolved in good faith within 10 days.",
            )

        return HeuristicAssessment(
            category="PAYMENT_TERMS",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard commercial payment terms with customary invoice turnaround.",
            suggested_pushback=None,
        )

    def _evaluate_tenancy(self, body_lower: str) -> HeuristicAssessment:
        if any(k in body_lower for k in ["unannounced", "at any hour", "without notice"]):
            return HeuristicAssessment(
                category="MISC",
                risk_level="HIGH",
                unfairness_score=90,
                plain_summary="Allows landlord entry without 24 hours prior notice, infringing upon quiet enjoyment rights.",
                suggested_pushback="Landlord may enter the premises only with at least twenty-four (24) hours advance written notice, during normal business hours, except for life-safety emergencies.",
            )
        if any(k in body_lower for k in ["wear and tear", "carpet", "deposit"]):
            return HeuristicAssessment(
                category="PAYMENT_TERMS",
                risk_level="MEDIUM",
                unfairness_score=60,
                plain_summary="Allows deductions from security deposit for normal wear and tear.",
                suggested_pushback="Security deposit deductions shall strictly apply to verified damage exceeding normal wear and tear, accompanied by itemized contractor receipts.",
            )
        return HeuristicAssessment(
            category="MISC",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard residential covenant.",
            suggested_pushback=None,
        )


heuristic_engine = HeuristicEngine()
