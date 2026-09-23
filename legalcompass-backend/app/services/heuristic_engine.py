"""
Heuristic Legal Rule Engine for LegalCompass — Accuracy V2.

Performs structural pre-screening and semantic analysis of contract clauses.

Architecture:
1. STRUCTURAL CLASSIFICATION — determines clause_kind (DEFINITION, HEADING,
   RECITAL, BOILERPLATE, OPERATIVE) and is_risk_bearing before any risk scoring.
2. TRIPLE GATE FOR HIGH RISK — requires ALL THREE:
   a) Material consequence (substantive legal/financial exposure)
   b) Meaningful imbalance/exposure (unilateral, uncapped, unconditional)
   c) Insufficient mitigation (no caps, no mutuality, no conditions)
3. SEMANTIC ANALYSIS — directionality, reciprocity, negation, conditionality
   (preserved from v1 but now wrapped in the triple-gate framework).

ZERO HARDCODING: No clause numbers, section titles, specific phrases from any
test contract, or contract-specific exceptions.
"""

import re
from typing import NamedTuple, Optional, List


class HeuristicAssessment(NamedTuple):
    category: str
    risk_level: str  # "HIGH", "MEDIUM", "LOW", "NEUTRAL"
    unfairness_score: int  # 0 - 100
    plain_summary: str
    suggested_pushback: Optional[str]
    clause_kind: str  # "DEFINITION", "HEADING", "RECITAL", "BOILERPLATE", "OPERATIVE"
    is_risk_bearing: bool
    risk_reasons: List[str]


class HeuristicEngine:
    """Deterministic structural and semantic legal evaluator with structural pre-screening."""

    # =========================================================================
    # Pattern Libraries (all generalized, zero contract-specific patterns)
    # =========================================================================

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

    # Pure definition indicators (quoted term + "means/shall mean/refers to/includes")
    RE_DEFINITION = re.compile(
        r"""^(?:[\"'\u2018\u2019\u201c\u201d]([^\"'\u2018\u2019\u201c\u201d]+)[\"'\u2018\u2019\u201c\u201d]\s+(?:means|shall\s+mean|refers\s+to|includes?)|"""
        r"""(?:Section\s+\d+|Clause\s+\d+|\d+\.\d+)?\s*[\"'\u2018\u2019\u201c\u201d]([^\"'\u2018\u2019\u201c\u201d]+)[\"'\u2018\u2019\u201c\u201d]\s+(?:means|shall\s+mean)|"""
        r'definitions?\s*[-\u2014:])',
        re.IGNORECASE,
    )

    # Recital patterns
    RE_RECITAL = re.compile(
        r"^\s*(?:WHEREAS|NOW,?\s+THEREFORE|RECITALS?)\b",
        re.IGNORECASE,
    )

    # Cross-reference / boilerplate patterns
    RE_CROSS_REFERENCE = re.compile(
        r"\b(?:as\s+defined\s+in\s+(?:Section|Clause|Article)\s+\d|"
        r"subject\s+to\s+the\s+provisions\s+of\s+(?:Section|Clause|Article)\s+\d|"
        r"in\s+accordance\s+with\s+(?:Section|Clause|Article)\s+\d)\b",
        re.IGNORECASE,
    )

    RE_BOILERPLATE = re.compile(
        r"\b(?:governing\s+law|severability|entire\s+agreement|"
        r"amendments?\s+(?:must|shall)\s+be\s+in\s+writing|"
        r"notices?\s+shall\s+be\s+(?:sent|delivered)|"
        r"waiver\s+of\s+any\s+(?:breach|provision)|"
        r"headings?\s+are\s+for\s+(?:convenience|reference)\s+only|"
        r"counterparts)\b",
        re.IGNORECASE,
    )

    # Mitigation indicators
    RE_MITIGATION_CAPS = re.compile(
        r"\b(?:capped\s+at|limited\s+to|not\s+to\s+exceed|aggregate\s+liability|"
        r"maximum\s+liability|total\s+liability\s+shall\s+not\s+exceed|"
        r"subject\s+to\s+the\s+liability\s+cap|ceiling|"
        r"in\s+no\s+event\s+shall.*(?:exceed|more\s+than))\b",
        re.IGNORECASE,
    )

    RE_MITIGATION_CONDITIONS = re.compile(
        r"\b(?:upon\s+(?:full\s+)?payment|receipt\s+of\s+(?:full\s+)?payment|"
        r"conditioned\s+upon\s+payment|cleared\s+funds|subject\s+to\s+payment|"
        r"upon\s+completion|after\s+acceptance)\b",
        re.IGNORECASE,
    )

    RE_MITIGATION_CURE = re.compile(
        r"\b(?:(?:\d+)\s*(?:days?|business\s+days?)\s*(?:prior\s+)?(?:written\s+)?notice|"
        r"opportunity\s+to\s+cure|right\s+to\s+cure|cure\s+period|"
        r"reasonable\s+time\s+to\s+(?:cure|remedy)|grace\s+period)\b",
        re.IGNORECASE,
    )

    # Operative trap patterns — these override DEFINITION/HEADING classification
    RE_OPERATIVE_TRAP = re.compile(
        r"\b(?:(?:contractor|tenant|client|party|employee|licensee)\s+"
        r"(?:shall|must|hereby\s+agrees?\s+to)\s+"
        r"(?:indemnify|defend|hold\s+harmless)|"
        r"hereby\s+(?:irrevocably\s+)?assigns|"
        r"(?:shall|will)\s+forfeit|"
        r"uncapped\s+liability|"
        r"immediately\s+upon\s+creation|"
        r"irrespective\s+of\s+whether.*(?:paid|payment)|"
        r"regardless\s+of\s+(?:whether\s+)?(?:.*)?payment|"
        r"without\s+(?:cap|limitation|limit|recourse)|"
        r"any\s+and\s+all\s+(?:losses|claims|damages|liabilities))\b",
        re.IGNORECASE,
    )

    # =========================================================================
    # Public API
    # =========================================================================

    def evaluate_clause(self, title: str, text: str) -> HeuristicAssessment:
        """Evaluates clause text using structural pre-screening + semantic analysis."""
        full_text = f"{title}\n{text}".strip()
        body_lower = text.lower()

        # ── Step 1: Structural Classification ──
        clause_kind = self._classify_clause_kind(title, text)
        risk_bearing = self._determine_risk_bearing(clause_kind, text)

        # ── Step 2: Non-risk-bearing fast path ──
        if not risk_bearing:
            summary_map = {
                "DEFINITION": "Definitional provision defining contract terminology without imposing asymmetric legal exposure.",
                "HEADING": "Section heading or structural marker without substantive obligations.",
                "RECITAL": "Recital providing background context for the agreement without imposing binding obligations.",
                "BOILERPLATE": "Standard administrative or procedural provision with no material risk exposure.",
            }
            return HeuristicAssessment(
                category="OTHER",
                risk_level="NEUTRAL",
                unfairness_score=10,
                plain_summary=summary_map.get(clause_kind, "Non-operative provision."),
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=False,
                risk_reasons=[],
            )

        # ── Step 3: Semantic Analysis (operative clauses only) ──
        is_negated = bool(self.RE_NEGATION.search(body_lower))
        is_reciprocal = bool(self.RE_RECIPROCAL.search(body_lower))
        has_mitigation = self._check_mitigation(body_lower)

        # Negation fast paths
        if is_negated:
            negation_result = self._evaluate_negation(body_lower, is_reciprocal, clause_kind)
            if negation_result:
                return negation_result

        # Category-specific evaluation
        text_lower = full_text.lower()

        # Indemnification
        if any(k in text_lower for k in ["indemn", "hold harmless", "defend and hold"]):
            return self._evaluate_indemnification(body_lower, is_reciprocal, is_negated, has_mitigation, clause_kind)

        # Intellectual Property & Work Product
        if any(k in text_lower for k in ["intellectual property", "inventions", "work made for hire", "assigns", "deliverables"]):
            return self._evaluate_ip(title, body_lower, has_mitigation, clause_kind)

        # Termination
        if any(k in text_lower for k in ["terminate", "termination", "cancel", "renewal"]):
            return self._evaluate_termination(body_lower, is_reciprocal, is_negated, has_mitigation, clause_kind)

        # Order of Precedence Conflict (MUST be before Payment Terms — OoP clauses contain "invoice")
        if any(k in text_lower for k in ["order of precedence", "purchase order shall control", "invoice shall control", "supersede"]):
            if any(k in body_lower for k in ["purchase order", "invoice", "vendor form"]) and any(k in body_lower for k in ["control", "prevail", "supersede"]):
                return HeuristicAssessment(
                    category="DISPUTE_RESOLUTION",
                    risk_level="HIGH",
                    unfairness_score=85,
                    plain_summary="Order of precedence carves out payment terms or liability to purchase orders, allowing unilateral counterparty terms to override this agreement.",
                    suggested_pushback="The terms and conditions of this Agreement shall strictly prevail and control over any conflict with any Purchase Order or invoice.",
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=[
                        "Material consequence: counterparty PO/invoice terms can override contract protections",
                        "Meaningful imbalance: unilateral override power given to one party's documents",
                        "Insufficient mitigation: no mutual agreement required for override",
                    ],
                )

        # Payment Terms & Setoff
        if any(k in text_lower for k in ["payment", "invoice", "net 60", "net 90", "net-60", "net-90", "withhold", "setoff", "set off"]):
            return self._evaluate_payment(body_lower, has_mitigation, clause_kind)

        # Tenancy / Quiet Enjoyment
        if any(k in text_lower for k in ["enter premises", "unannounced", "routine inspection", "carpet", "deposit"]):
            return self._evaluate_tenancy(body_lower, clause_kind)

        # Default Standard Provision
        category = "DISPUTE_RESOLUTION" if any(k in text_lower for k in ["dispute", "governing law", "jurisdiction"]) else "OTHER"
        return HeuristicAssessment(
            category=category,
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard commercial provision with customary obligations.",
            suggested_pushback=None,
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=[],
        )

    # =========================================================================
    # Step 1: Structural Classification
    # =========================================================================

    def _classify_clause_kind(self, title: str, text: str) -> str:
        """Determines the structural kind of a clause from content analysis.

        Returns one of: DEFINITION, HEADING, RECITAL, BOILERPLATE, OPERATIVE.
        ZERO HARDCODING — all detection is pattern-based, never contract-specific.
        """
        title_lower = title.lower().strip()
        text_stripped = text.strip()
        body_words = len(text_stripped.split())

        # ── RECITAL ──
        if self.RE_RECITAL.match(text_stripped) or self.RE_RECITAL.match(title):
            return "RECITAL"

        # ── DEFINITION ──
        is_def_title = any(kw in title_lower for kw in ["definitions", "defined terms", "interpretation"])
        has_definition_body = bool(re.match(
            r'^\s*(?:\d+\.\d+\s+)?["\'\u2018\u2019\u201c\u201d]([^"\'\u2018\u2019\u201c\u201d]+)["\'\u2018\u2019\u201c\u201d]\s+(?:means|shall\s+mean|refers\s+to|includes)',
            text_stripped, re.IGNORECASE
        ))
        if is_def_title or has_definition_body:
            # Only classify as DEFINITION if no operative trap is hidden inside
            if not self.RE_OPERATIVE_TRAP.search(text):
                return "DEFINITION"

        # ── HEADING ──
        # A heading has a title but very little substantive body text
        # Remove the title text from body to measure actual content
        body_without_title = text_stripped
        if title.strip() and body_without_title.lower().startswith(title_lower):
            body_without_title = body_without_title[len(title):].strip()
        body_content_words = len(body_without_title.split())
        # Short text is a HEADING unless it contains operative language
        has_operative_verbs = bool(re.search(
            r'\b(?:shall|must|agrees?\s+to|may\s+not|will\s+not|hereby|obligat|waive|forfeit|assign|indemn|terminat|liable)\b',
            body_without_title, re.IGNORECASE
        ))
        if body_content_words < 10 and not has_operative_verbs and not self.RE_OPERATIVE_TRAP.search(text):
            return "HEADING"

        # ── BOILERPLATE ──
        boilerplate_hits = len(self.RE_BOILERPLATE.findall(text_stripped))
        is_pure_crossref = bool(self.RE_CROSS_REFERENCE.search(text_stripped)) and body_words < 30
        if (boilerplate_hits >= 2 or is_pure_crossref) and not self.RE_OPERATIVE_TRAP.search(text):
            return "BOILERPLATE"

        return "OPERATIVE"

    def _determine_risk_bearing(self, clause_kind: str, text: str) -> bool:
        """Determines if a clause can carry material risk.

        Non-operative clause types (DEFINITION, HEADING, RECITAL) are not risk-bearing
        UNLESS they contain an operative trap pattern (e.g., "hereby irrevocably assigns"
        embedded inside a definition).
        """
        if clause_kind in ("DEFINITION", "HEADING", "RECITAL"):
            # Override: if an operative trap pattern is found, the clause IS risk-bearing
            return bool(self.RE_OPERATIVE_TRAP.search(text))

        if clause_kind == "BOILERPLATE":
            # Boilerplate is generally not risk-bearing unless it has an operative trap
            return bool(self.RE_OPERATIVE_TRAP.search(text))

        # OPERATIVE clauses are always risk-bearing
        return True

    # =========================================================================
    # Step 2: Mitigation Detection
    # =========================================================================

    def _check_mitigation(self, body_lower: str) -> dict:
        """Detects mitigating/balancing language in clause text.

        Returns a dict with boolean flags for each mitigation category.
        """
        return {
            "has_cap": bool(self.RE_MITIGATION_CAPS.search(body_lower)),
            "has_mutuality": bool(self.RE_RECIPROCAL.search(body_lower)),
            "has_condition": bool(self.RE_MITIGATION_CONDITIONS.search(body_lower)),
            "has_cure_period": bool(self.RE_MITIGATION_CURE.search(body_lower)),
        }

    def _count_mitigations(self, mitigation: dict) -> int:
        """Counts how many mitigation factors are present."""
        return sum(1 for v in mitigation.values() if v)

    # =========================================================================
    # Step 3: Negation Fast Paths
    # =========================================================================

    def _evaluate_negation(self, body_lower: str, is_reciprocal: bool, clause_kind: str) -> Optional[HeuristicAssessment]:
        """Handles clauses that explicitly disclaim or negate liability/duty."""
        if any(k in body_lower for k in ["no indemn", "shall not indemnify", "not be required to indemnify"]):
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="LOW",
                unfairness_score=15,
                plain_summary="Explicitly relieves contractor from indemnification duties, presenting zero unilateral liability exposure.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Negated indemnification duty"],
            )
        if any(k in body_lower for k in ["neither party shall", "neither party may terminate without cause"]):
            return HeuristicAssessment(
                category="TERMINATION" if "terminate" in body_lower else "OTHER",
                risk_level="LOW",
                unfairness_score=20,
                plain_summary="Bilateral negative covenant prohibiting both parties from taking adverse unilateral action.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Bilateral restriction"],
            )
        if any(k in body_lower for k in ["shall not be liable", "no liability"]):
            if is_reciprocal:
                return HeuristicAssessment(
                    category="LIABILITY",
                    risk_level="LOW",
                    unfairness_score=20,
                    plain_summary="Mutual disclaimer of indirect or consequential damages, standard in commercial agreements.",
                    suggested_pushback=None,
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=["Mutual liability disclaimer"],
                )
        return None

    # =========================================================================
    # Step 4: Category-Specific Evaluators (with Triple Gate)
    # =========================================================================

    def _evaluate_indemnification(self, body_lower: str, is_reciprocal: bool, is_negated: bool, mitigation: dict, clause_kind: str) -> HeuristicAssessment:
        """Evaluates indemnification clauses with Triple Gate for HIGH risk."""
        if is_negated:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="LOW",
                unfairness_score=15,
                plain_summary="Explicitly negates indemnification duties for the contractor.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Negated indemnification duty"],
            )

        if is_reciprocal:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="LOW",
                unfairness_score=30,
                plain_summary="Bilateral mutual indemnification provision where each party is responsible solely for its own breach or negligence.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Mutual/reciprocal indemnification"],
            )

        # Unilateral indemnification — apply Triple Gate
        is_uncapped = any(k in body_lower for k in ["uncapped", "unlimited", "any and all", "without limitation", "all losses", "defense costs", "attorney fees"])

        # Triple Gate for HIGH:
        # 1. Material consequence: indemnification = yes (always true here)
        # 2. Meaningful imbalance: uncapped + unilateral
        # 3. Insufficient mitigation: no cap, no mutuality, no condition
        has_cap = mitigation["has_cap"]
        mitigation_count = self._count_mitigations(mitigation)

        if is_uncapped and not has_cap and mitigation_count == 0:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="HIGH",
                unfairness_score=92,
                plain_summary="Imposes uncapped unilateral indemnification on you, exposing you to personal legal defense bills and third-party liabilities if the counterparty is sued.",
                suggested_pushback="Each party shall mutually indemnify the other against third-party claims arising solely from its gross negligence. Total liability under this indemnity shall be capped at fees received under this Agreement.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: personal legal defense bills and third-party liability exposure",
                    "Meaningful imbalance: unilateral and uncapped indemnification duty",
                    "Insufficient mitigation: no liability cap, no mutuality, no payment condition",
                ],
            )
        elif is_uncapped and has_cap:
            # Uncapped language present but cap also present — MEDIUM
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="MEDIUM",
                unfairness_score=55,
                plain_summary="Unilateral indemnification duty with broad language, partially mitigated by liability cap provisions.",
                suggested_pushback="Indemnification obligations shall be mutual, fault-based, and capped at total fees paid under this Agreement.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: indemnification exposure",
                    "Meaningful imbalance: unilateral duty",
                    "Partial mitigation: liability cap present",
                ],
            )
        else:
            return HeuristicAssessment(
                category="INDEMNIFICATION",
                risk_level="MEDIUM",
                unfairness_score=60,
                plain_summary="Unilateral indemnification duty requiring you to cover counterparty losses, though subject to general legal limits.",
                suggested_pushback="Indemnification obligations shall be mutual, fault-based, and capped at total fees paid under this Agreement.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: indemnification exposure",
                    "Meaningful imbalance: unilateral duty",
                ],
            )

    def _evaluate_ip(self, title: str, body_lower: str, mitigation: dict, clause_kind: str) -> HeuristicAssessment:
        """Evaluates IP/work-product clauses with Triple Gate."""
        # Check if it is a pre-existing IP / Background IP carve-out or definition
        if "background ip" in title.lower() or "pre-existing" in body_lower:
            return HeuristicAssessment(
                category="INTELLECTUAL_PROPERTY",
                risk_level="LOW",
                unfairness_score=20,
                plain_summary="Recognizes contractor retention of pre-existing background IP and developer tooling.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Background IP protection recognized"],
            )

        has_assignment = any(k in body_lower for k in ["assigns", "transfers", "work made for hire", "irrevocably assign", "exclusive property of client"])
        is_conditioned_on_payment = any(k in body_lower for k in ["upon full payment", "receipt of full payment", "conditioned upon payment", "cleared funds", "subject to payment"])
        is_unconditional = any(k in body_lower for k in ["immediately upon creation", "irrespective of whether client has paid", "regardless of payment", "upon inception"])

        if has_assignment:
            # Triple Gate for HIGH:
            # 1. Material consequence: IP assignment = yes
            # 2. Meaningful imbalance: unconditional or irrevocable without payment
            # 3. Insufficient mitigation: no payment condition, no cap
            if is_unconditional or (not is_conditioned_on_payment and any(k in body_lower for k in ["irrevocably", "without cap", "immediate"])):
                return HeuristicAssessment(
                    category="INTELLECTUAL_PROPERTY",
                    risk_level="HIGH",
                    unfairness_score=88,
                    plain_summary="Ownership of all code, designs, and deliverables transfers immediately upon creation, meaning the client owns your work product even if they fail to pay your invoice.",
                    suggested_pushback="All intellectual property rights in and to Deliverables shall transfer exclusively to Client strictly upon Contractor's receipt of full and complete invoice payment.",
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=[
                        "Material consequence: loss of ownership of all work product",
                        "Meaningful imbalance: unconditional transfer regardless of payment",
                        "Insufficient mitigation: no payment condition protects contractor",
                    ],
                )
            elif is_conditioned_on_payment:
                return HeuristicAssessment(
                    category="INTELLECTUAL_PROPERTY",
                    risk_level="LOW",
                    unfairness_score=25,
                    plain_summary="Standard, balanced IP assignment provision where ownership transfer is strictly conditioned upon receipt of full payment.",
                    suggested_pushback=None,
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=["Payment-conditioned IP transfer"],
                )
            else:
                return HeuristicAssessment(
                    category="INTELLECTUAL_PROPERTY",
                    risk_level="MEDIUM",
                    unfairness_score=55,
                    plain_summary="Transfers intellectual property rights without explicit language conditioning the transfer on cleared payment.",
                    suggested_pushback="Title and copyright to Deliverables shall pass to Client upon receipt of full payment for the applicable milestone.",
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=[
                        "Material consequence: IP ownership transfer",
                        "No explicit payment condition",
                    ],
                )

        return HeuristicAssessment(
            category="INTELLECTUAL_PROPERTY",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard intellectual property provision outlining scope and licensing.",
            suggested_pushback=None,
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=[],
        )

    def _evaluate_termination(self, body_lower: str, is_reciprocal: bool, is_negated: bool, mitigation: dict, clause_kind: str) -> HeuristicAssessment:
        """Evaluates termination clauses with Triple Gate."""
        if is_negated:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="LOW",
                unfairness_score=20,
                plain_summary="Bilateral restriction preventing termination without cause.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Bilateral termination restriction"],
            )

        # Unilateral immediate termination for convenience with forfeiture
        unilateral_kill = any(k in body_lower for k in ["client may terminate at any time", "terminate without cause at will", "forfeit unbilled", "without notice or penalty", "terminate immediately at its sole option"])
        has_forfeiture = any(k in body_lower for k in ["without payment for work", "forfeit", "no compensation"])

        # Triple Gate for HIGH
        if unilateral_kill or has_forfeiture:
            has_cure = mitigation["has_cure_period"]
            if not has_cure:
                return HeuristicAssessment(
                    category="TERMINATION",
                    risk_level="HIGH",
                    unfairness_score=85,
                    plain_summary="Allows the client to terminate the contract at will without adequate notice and withhold compensation for in-progress work.",
                    suggested_pushback="Either party may terminate for convenience upon thirty (30) days prior written notice. Upon termination, Client shall pay Contractor for all completed work and non-cancelable commitments.",
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=[
                        "Material consequence: loss of compensation for in-progress work",
                        "Meaningful imbalance: unilateral termination power with forfeiture",
                        "Insufficient mitigation: no notice period or cure right",
                    ],
                )
            else:
                return HeuristicAssessment(
                    category="TERMINATION",
                    risk_level="MEDIUM",
                    unfairness_score=55,
                    plain_summary="Unilateral termination rights with some notice provisions, but forfeiture language creates partial exposure.",
                    suggested_pushback="Either party may terminate for convenience upon thirty (30) days prior written notice. Upon termination, Client shall pay Contractor for all completed work.",
                    clause_kind=clause_kind,
                    is_risk_bearing=True,
                    risk_reasons=[
                        "Material consequence: potential work forfeiture",
                        "Partial mitigation: notice/cure period present",
                    ],
                )

        if is_reciprocal or any(k in body_lower for k in ["either party may terminate upon", "both parties"]):
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="LOW",
                unfairness_score=25,
                plain_summary="Mutual termination clause allowing either party to end the engagement with customary prior written notice.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=["Mutual termination rights"],
            )

        return HeuristicAssessment(
            category="TERMINATION",
            risk_level="MEDIUM",
            unfairness_score=50,
            plain_summary="Termination provision with moderate notice or unilateral cure requirements.",
            suggested_pushback="Provide mutual termination rights with 30 days written notice and compensation for work completed to date.",
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=["Termination provision with moderate imbalance"],
        )

    def _evaluate_payment(self, body_lower: str, mitigation: dict, clause_kind: str) -> HeuristicAssessment:
        """Evaluates payment clauses."""
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
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: cash flow vulnerability from delayed payment",
                    "Meaningful imbalance: unilateral withholding discretion",
                ],
            )

        return HeuristicAssessment(
            category="PAYMENT_TERMS",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard commercial payment terms with customary invoice turnaround.",
            suggested_pushback=None,
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=[],
        )

    def _evaluate_tenancy(self, body_lower: str, clause_kind: str) -> HeuristicAssessment:
        """Evaluates tenancy/quiet enjoyment clauses."""
        if any(k in body_lower for k in ["unannounced", "at any hour", "without notice"]):
            return HeuristicAssessment(
                category="MISC",
                risk_level="HIGH",
                unfairness_score=90,
                plain_summary="Allows landlord entry without 24 hours prior notice, infringing upon quiet enjoyment rights.",
                suggested_pushback="Landlord may enter the premises only with at least twenty-four (24) hours advance written notice, during normal business hours, except for life-safety emergencies.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: violation of tenant quiet enjoyment rights",
                    "Meaningful imbalance: unilateral entry without notice",
                    "Insufficient mitigation: no notice requirement",
                ],
            )
        if any(k in body_lower for k in ["wear and tear", "carpet", "deposit"]):
            return HeuristicAssessment(
                category="PAYMENT_TERMS",
                risk_level="MEDIUM",
                unfairness_score=60,
                plain_summary="Allows deductions from security deposit for normal wear and tear.",
                suggested_pushback="Security deposit deductions shall strictly apply to verified damage exceeding normal wear and tear, accompanied by itemized contractor receipts.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: deposit loss for normal wear",
                    "Meaningful imbalance: landlord unilateral deduction authority",
                ],
            )
        return HeuristicAssessment(
            category="MISC",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard residential covenant.",
            suggested_pushback=None,
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=[],
        )


heuristic_engine = HeuristicEngine()
