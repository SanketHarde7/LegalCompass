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
from dataclasses import dataclass
from typing import NamedTuple, Optional, List, Any, Dict, Tuple


@dataclass
class ResolvedReference:
    target_clause: Any
    reference_label: str  # e.g., "Section 4" or "4"
    relation: str  # "expands" | "limits" | "overrides" | "mitigates" | "unrelated"
    explanation: str


def _get_clause_attr(c: Any, attr: str, default: Any = "") -> Any:
    if isinstance(c, dict):
        return c.get(attr, default)
    return getattr(c, attr, default)


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

    # Term duration and initial effective period indicators
    RE_TERM_DURATION = re.compile(
        r"\b(?:"
        r"commences?\s+on|"
        r"effective\s+date\s+of\s+this\s+agreement|"
        r"(?:initial\s+term|initial\s+period)\s+of|"
        r"shall\s+(?:remain\s+in\s+effect|continue|endure)\s+for\s+(?:an?\s+)?(?:initial\s+)?(?:period|term)|"
        r"term\s+of\s+this\s+agreement\s+shall\s+be|"
        r"shall\s+expire\s+on|"
        r"expiration\s+date|"
        r"effective\s+until\s+(?:terminated|expired)"
        r")\b",
        re.IGNORECASE,
    )

    # Affirmative termination covenants and procedures
    RE_TERMINATION_COVENANT = re.compile(
        r"\b(?:"
        r"(?:may|has\s+the\s+right\s+to|entitled\s+to|reserves\s+the\s+right\s+to)\s+terminate|"
        r"terminate\s+(?:this\s+agreement|the\s+agreement|immediately|at\s+any\s+time|for\s+convenience|for\s+cause|without\s+cause)|"
        r"(?:right|option)\s+to\s+terminate|"
        r"(?:notice|grounds)\s+of\s+termination|"
        r"in\s+the\s+event\s+of\s+termination|"
        r"upon\s+termination|"
        r"following\s+termination|"
        r"cancel\s+(?:this\s+agreement|the\s+agreement)|"
        r"cancellation\s+of\s+this\s+agreement"
        r")\b",
        re.IGNORECASE,
    )

    # Renewal covenants and extensions
    RE_RENEWAL_COVENANT = re.compile(
        r"\b(?:"
        r"auto(?:matically)?\s*[-]?\s*renew(?:s|al|ed|ing)?|"
        r"renew(?:s|al|ed|ing)?\s+for\s+(?:an?\s+)?(?:additional|successive)|"
        r"successive\s+(?:term|terms|period|periods)|"
        r"extend(?:s|ed|ing)?\s+the\s+term|"
        r"extension\s+of\s+(?:the\s+)?term|"
        r"option\s+to\s+renew|"
        r"right\s+to\s+renew|"
        r"notice\s+of\s+non-renewal"
        r")\b",
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

    # Substantive operative consequence indicators
    RE_SUBSTANTIVE_CONSEQUENCE = re.compile(
        r"\b(?:"
        r"reimburse(?:ment|s)?|pay(?:s|ment|ing)?|invoic(?:e|ing|es)?|fees?|expenses?|compensation|"
        r"assign(?:s|ment|ing)?|transfers?|grant(?:s|ing)?\s+(?:a\s+)?license|work\s+made\s+for\s+hire|"
        r"indemnif(?:y|ies|ication)|hold\s+harmless|defend\s+against|"
        r"terminat(?:e|es|ion|ing)|cancel(?:s|lation)?|renew(?:s|al)?|"
        r"liab(?:le|ility)|damages?|penalt(?:y|ies)|forfeit(?:s|ure|ing)?|liquidated\s+damages|default|"
        r"injuncti(?:on|ve)|specific\s+performance|remed(?:y|ies)|breach|"
        r"waiv(?:e|es|ed|ing)\s+(?:any\s+)?(?:right|claim|defense|jury|trial|counterclaim|compensation)|"
        r"shall\s+not|must\s+not|may\s+not|prohibited\s+from|restricted\s+from|refrain\s+from|will\s+not"
        r")\b",
        re.IGNORECASE,
    )

    # Covenant / duty verbs
    RE_COVENANT_VERBS = re.compile(
        r"\b(?:shall|must|agrees?\s+to|hereby\s+agrees?|covenants?\s+to|is\s+required\s+to|entitled\s+to|has\s+the\s+right\s+to)\b",
        re.IGNORECASE,
    )

    # Pure administrative boilerplate patterns (without substantive legal consequence)
    RE_PURE_GOVERNING_LAW = re.compile(
        r"\b(?:governed\s+by|construed\s+in\s+accordance\s+with|laws\s+of\s+(?:the\s+State\s+of\s+)?[A-Z]|choice\s+of\s+law|"
        r"jurisdiction\s+of\s+the\s+courts?|exclusive\s+venue)\b",
        re.IGNORECASE,
    )

    RE_PURE_NOTICES = re.compile(
        r"\b(?:notices?\s+(?:shall|must|may)\s+be\s+(?:in\s+writing|given|delivered|sent|deemed\s+given)|"
        r"addressed\s+to\s+the\s+(?:parties|addresses|preamble))\b",
        re.IGNORECASE,
    )

    RE_PURE_SEVERABILITY = re.compile(
        r"\b(?:severability|if\s+any\s+provision.*(?:invalid|illegal|unenforceable)|"
        r"remaining\s+provisions\s+shall\s+continue)\b",
        re.IGNORECASE,
    )

    RE_PURE_COUNTERPARTS = re.compile(
        r"\b(?:counterparts|facsimile|electronic\s+signature|executed\s+in.*counterparts)\b",
        re.IGNORECASE,
    )

    RE_PURE_ENTIRE_AGREEMENT = re.compile(
        r"\b(?:entire\s+agreement|merger\s+clause|supersedes?\s+all\s+prior\s+(?:agreements|understandings|negotiations))\b",
        re.IGNORECASE,
    )

    RE_PURE_CROSS_REF_BODY = re.compile(
        r"^\s*(?:as\s+defined\s+in|see|refer\s+to|capitalized\s+terms.*meanings?\s+(?:assigned|set\s+forth)\s+in)\s+(?:Section|Clause|Article)\s+[0-9IVXLCDM]+",
        re.IGNORECASE,
    )

    # Cross-reference mention detector & label extraction
    RE_CROSS_REF_MENTION = re.compile(
        r"\b(?:Section|Clause|Article|subsection|Paragraph)\s+([0-9]+(?:\.[0-9]+)*|[IVXLCDM]+)\b",
        re.IGNORECASE,
    )

    RE_CLAUSE_LABEL = re.compile(
        r"^(?:Section|Clause|Article|subsection|Paragraph)?\s*([0-9]+(?:\.[0-9]+)*|[IVXLCDM]+)\b",
        re.IGNORECASE,
    )

    # =========================================================================
    # Public API
    # =========================================================================

    def evaluate_clause(
        self,
        title: str,
        text: str,
        all_clauses: Optional[List[Any]] = None,
        _label_index: Optional[Dict[str, Any]] = None,
    ) -> HeuristicAssessment:
        """Evaluates clause text using structural pre-screening + semantic analysis + cross-reference resolution."""
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

        # Dynamic cross-reference resolution against active document clauses
        resolved_refs: List[ResolvedReference] = []
        if all_clauses or _label_index:
            resolved_refs = self.resolve_referenced_clauses(
                {"title": title, "text": text}, all_clauses, precomputed_index=_label_index
            )
            for ref in resolved_refs:
                if ref.relation in ("mitigates", "limits"):
                    target_text_lower = str(_get_clause_attr(ref.target_clause, "text", "")).lower()
                    target_mit = self._check_mitigation(target_text_lower)
                    for k, v in target_mit.items():
                        if v:
                            has_mitigation[k] = True

        # Negation fast paths
        if is_negated:
            negation_result = self._evaluate_negation(body_lower, is_reciprocal, clause_kind)
            if negation_result:
                return negation_result

        # ── Step 4: Category-Specific Semantic Evaluation (primarily based on clause body) ──

        # 1. Order of Precedence Conflict (evaluated before payment, since OoP contains "invoice")
        has_oop_body = (
            any(k in body_lower for k in ["order of precedence", "purchase order shall control", "invoice shall control", "supersede and strictly control", "prevail over"])
            or (any(k in body_lower for k in ["purchase order", "invoice", "vendor form"]) and any(k in body_lower for k in ["control", "prevail", "supersede", "conflict", "inconsistency"]))
        )
        if has_oop_body and any(k in body_lower for k in ["control", "prevail", "supersede"]):
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

        # 2. Indemnification (must have substantive indemnification language in body)
        if any(k in body_lower for k in ["indemn", "hold harmless", "defend and hold"]):
            return self._evaluate_indemnification(body_lower, is_reciprocal, is_negated, has_mitigation, clause_kind)

        # 3. Intellectual Property & Work Product (must have substantive IP language in body)
        if any(k in body_lower for k in [
            "work made for hire", "irrevocably assign", "assigns all", "assign all",
            "intellectual property", "inventions", "deliverables", "proprietary rights",
            "ownership of work", "background ip",
        ]):
            return self._evaluate_ip(title, body_lower, has_mitigation, clause_kind)

        # 4. Term, Renewal & Termination (distinguish duration, renewal covenants, and termination covenants)
        has_term_duration = bool(self.RE_TERM_DURATION.search(body_lower))
        has_renewal_covenant = bool(self.RE_RENEWAL_COVENANT.search(body_lower))
        has_termination_covenant = bool(self.RE_TERMINATION_COVENANT.search(body_lower))

        # 4a. Pure Term Duration (without renewal or termination covenants)
        if has_term_duration and not has_renewal_covenant and not has_termination_covenant:
            return self._evaluate_term_duration(body_lower, clause_kind)

        # 4b. Renewal / Extension Covenants
        if has_renewal_covenant:
            return self._evaluate_renewal(body_lower, is_reciprocal, has_mitigation, clause_kind)

        # 4c. Affirmative Termination Covenants
        if has_termination_covenant:
            return self._evaluate_termination(body_lower, is_reciprocal, is_negated, has_mitigation, clause_kind)

        # 5. Payment Terms & Setoff
        if any(k in body_lower for k in ["payment", "invoice", "net 30", "net 60", "net 90", "net-30", "net-60", "net-90", "withhold", "setoff", "set off", "billing", "fees", "remit", "disbursement"]):
            return self._evaluate_payment(body_lower, has_mitigation, clause_kind)

        # 6. Tenancy / Quiet Enjoyment
        if any(k in body_lower for k in ["enter premises", "unannounced", "routine inspection", "carpet", "deposit", "quiet enjoyment"]):
            return self._evaluate_tenancy(body_lower, clause_kind)

        # 7. Default Standard Provision (catch-all for other operative clauses, e.g. governing law, notice, survival)
        category = "DISPUTE_RESOLUTION" if any(k in body_lower for k in ["dispute", "governing law", "jurisdiction", "arbitration", "venue"]) or any(k in title.lower() for k in ["dispute", "governing law", "jurisdiction", "arbitration"]) else "OTHER"
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

        # ── 1. RECITAL ──
        if self.RE_RECITAL.match(text_stripped) or self.RE_RECITAL.match(title):
            return "RECITAL"

        # ── 2. DEFINITION ──
        is_def_title = any(kw in title_lower for kw in ["definitions", "defined terms", "interpretation"])
        has_definition_body = bool(re.match(
            r'^\s*(?:\d+\.\d+\s+)?["\'\u2018\u2019\u201c\u201d]([^"\'\u2018\u2019\u201c\u201d]+)["\'\u2018\u2019\u201c\u201d]\s+(?:means|shall\s+mean|refers\s+to|includes)',
            text_stripped, re.IGNORECASE
        ))
        if is_def_title or has_definition_body:
            # Only classify as DEFINITION if genuinely definitional and non-operative
            if not self.RE_OPERATIVE_TRAP.search(text_stripped):
                return "DEFINITION"
            return "OPERATIVE"

        # ── 3. HEADING (only when no substantive body exists) ──
        body_without_title = text_stripped
        if title.strip() and body_without_title.lower().startswith(title_lower):
            body_without_title = body_without_title[len(title):].strip()
        body_content_words = len(body_without_title.split())
        has_operative_verbs = bool(re.search(
            r'\b(?:shall|must|agrees?\s+to|may\s+not|will\s+not|hereby|obligat|waive|forfeit|assign|indemn|terminat|liable)\b',
            body_without_title, re.IGNORECASE
        ))
        is_pure_heading = (
            text_stripped.lower() == title_lower
            or body_content_words == 0
            or (body_content_words <= 3 and not self._is_pure_boilerplate(title, text_stripped))
        )
        if is_pure_heading and not has_operative_verbs and not self.RE_OPERATIVE_TRAP.search(text_stripped):
            return "HEADING"

        # ── 4. OPERATIVE ──
        if self._is_operative_clause(title, text_stripped):
            return "OPERATIVE"

        # ── 5. BOILERPLATE ──
        if self._is_pure_boilerplate(title, text_stripped):
            return "BOILERPLATE"

        return "OPERATIVE"

    def _is_pure_boilerplate(self, title: str, text: str) -> bool:
        """Checks if a clause is purely administrative boilerplate with NO substantive covenants."""
        full_text = f"{title}\n{text}".strip()
        body_stripped = text.strip()

        # If it contains any substantive consequences or operative traps, it CANNOT be pure boilerplate
        if self.RE_OPERATIVE_TRAP.search(full_text) or self.RE_SUBSTANTIVE_CONSEQUENCE.search(full_text):
            return False

        # Check pure boilerplate categories
        if self.RE_PURE_GOVERNING_LAW.search(full_text):
            return True
        if self.RE_PURE_NOTICES.search(full_text):
            return True
        if self.RE_PURE_SEVERABILITY.search(full_text):
            return True
        if self.RE_PURE_COUNTERPARTS.search(full_text):
            return True
        if self.RE_PURE_ENTIRE_AGREEMENT.search(full_text):
            return True
        if self.RE_PURE_CROSS_REF_BODY.search(body_stripped):
            return True
        if self.RE_CROSS_REFERENCE.search(body_stripped) and len(body_stripped.split()) < 40:
            return True
        if len(self.RE_BOILERPLATE.findall(full_text)) >= 1:
            return True

        return False

    def _is_operative_clause(self, title: str, text: str) -> bool:
        """Determines if a clause contains substantive operative covenants or obligations."""
        full_text = f"{title}\n{text}".strip()

        # Operative trap is always operative
        if self.RE_OPERATIVE_TRAP.search(full_text):
            return True

        # Substantive consequence is operative
        if self.RE_SUBSTANTIVE_CONSEQUENCE.search(full_text):
            return True

        # Covenant verbs (shall, must, agrees to) are operative UNLESS pure administrative boilerplate
        if self.RE_COVENANT_VERBS.search(full_text):
            if self._is_pure_boilerplate(title, text):
                return False
            return True

        return False

    def _determine_risk_bearing(self, clause_kind: str, text: str) -> bool:
        """Determines if a clause can carry material risk.

        Non-operative clause types (DEFINITION, HEADING, RECITAL, BOILERPLATE) are not risk-bearing
        UNLESS they contain an operative trap pattern.
        """
        if clause_kind in ("DEFINITION", "HEADING", "RECITAL", "BOILERPLATE"):
            return bool(self.RE_OPERATIVE_TRAP.search(text))
        return True

    # =========================================================================
    # Cross-Reference Resolution
    # =========================================================================

    def build_label_index(self, all_clauses: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Builds a normalized-label -> clause lookup once per document, instead of
        rebuilding it on every evaluate_clause() call. Does NOT exclude any clause by id —
        self-exclusion happens at lookup time in resolve_referenced_clauses instead."""
        label_index: Dict[str, Any] = {}
        if not all_clauses:
            return label_index
        for c in all_clauses:
            c_label = self._extract_clause_label(c)
            if c_label:
                norm_label = c_label.lower().strip()
                if norm_label not in label_index:
                    label_index[norm_label] = c
        return label_index

    def resolve_referenced_clauses(
        self,
        current_clause: Any,
        all_clauses: Optional[List[Any]] = None,
        precomputed_index: Optional[Dict[str, Any]] = None,
    ) -> List[ResolvedReference]:
        """Dynamically identifies and resolves explicit cross-references (e.g. Section X, Clause Y)
        in current_clause against all_clauses parsed from the active document.

        Returns only confidently resolved references. Never guesses or fabricates target clauses.
        """
        if not all_clauses and not precomputed_index:
            return []

        text = str(_get_clause_attr(current_clause, "text", "")).strip()
        if not text:
            return []

        # Find explicit reference mentions
        matches = self.RE_CROSS_REF_MENTION.findall(text)
        if not matches:
            return []

        current_id = str(_get_clause_attr(current_clause, "id", ""))
        label_index = precomputed_index if precomputed_index is not None else self.build_label_index(all_clauses)

        resolved: List[ResolvedReference] = []
        seen_targets = set()

        for raw_ref in matches:
            norm_ref = raw_ref.lower().strip().rstrip(".")
            target_clause = label_index.get(norm_ref)
            if not target_clause:
                continue

            # Self-exclusion: skip if the resolved target is the current clause itself
            target_id = str(_get_clause_attr(target_clause, "id", "")) or norm_ref
            if current_id and target_id == current_id:
                continue
            if target_id in seen_targets:
                continue
            seen_targets.add(target_id)

            relation, explanation = self._determine_reference_relation(text, raw_ref, target_clause)
            resolved.append(
                ResolvedReference(
                    target_clause=target_clause,
                    reference_label=f"Section {raw_ref}",
                    relation=relation,
                    explanation=explanation,
                )
            )

        return resolved

    def _extract_clause_label(self, clause: Any) -> Optional[str]:
        """Extracts numbering/label from title or start of text without hardcoding."""
        title = str(_get_clause_attr(clause, "title", "")).strip()
        text = str(_get_clause_attr(clause, "text", "")).strip()

        # Check title first
        m = self.RE_CLAUSE_LABEL.match(title)
        if m:
            return m.group(1).rstrip(".")

        # Check start of text
        m_text = self.RE_CLAUSE_LABEL.match(text[:60])
        if m_text:
            return m_text.group(1).rstrip(".")

        return None

    def _determine_reference_relation(
        self,
        source_text: str,
        ref_label: str,
        target_clause: Any,
    ) -> Tuple[str, str]:
        """Analyzes relation between source clause and target clause:
        overrides | limits | mitigates | expands | unrelated
        """
        pattern = re.compile(
            rf"(?:.{{0,80}})?\b(?:Section|Clause|Article|subsection|Paragraph)\s+{re.escape(ref_label)}\b(?:.{{0,80}})?",
            re.IGNORECASE,
        )
        m = pattern.search(source_text)
        window = m.group(0).lower() if m else source_text.lower()

        # 1. Overrides
        if any(w in window for w in ["conflict", "inconsistency", "prevail", "supersede", "override", "govern", "notwithstanding"]):
            return "overrides", f"Current clause overrides or takes precedence over Section {ref_label}."

        # 2. Limits / Mitigates
        target_text_lower = str(_get_clause_attr(target_clause, "text", "")).lower()
        has_mitigating_language = any(
            pat.search(target_text_lower)
            for pat in [self.RE_MITIGATION_CAPS, self.RE_MITIGATION_CURE, self.RE_RECIPROCAL]
        )
        if any(w in window for w in ["subject to", "except as", "unless otherwise", "conditioned upon", "capped by", "provided that", "in accordance with"]):
            if has_mitigating_language:
                return "mitigates", f"Section {ref_label} provides mitigating protective terms (e.g. liability cap, cure period, or mutuality)."
            return "limits", f"Current clause is subject to or limited by Section {ref_label}."

        # 3. Expands
        if any(w in window for w in ["in addition to", "together with", "including without limitation", "as well as", "cumulative to"]):
            return "expands", f"Current clause expands obligations in conjunction with Section {ref_label}."

        # 4. Unrelated / Definitional
        return "unrelated", f"Standard reference to Section {ref_label}."

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

    def _evaluate_term_duration(self, body_lower: str, clause_kind: str) -> HeuristicAssessment:
        """Evaluates term-duration and expiration provisions.
        Classifies risk only when the substantive body contains concrete exposure/material imbalance.
        """
        # Forfeiture upon term expiration
        has_forfeiture = any(k in body_lower for k in ["forfeit", "forfeiture", "without payment", "no compensation", "relinquish all rights"])
        if has_forfeiture:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="HIGH",
                unfairness_score=85,
                plain_summary="Term expiration provision imposes forfeiture of compensation or accrued rights upon expiration.",
                suggested_pushback="Upon expiration of the term, Client shall promptly pay Contractor for all Services performed and Deliverables completed through the expiration date.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: forfeiture of compensation or rights upon term expiration",
                    "Meaningful imbalance: unilateral forfeiture obligation",
                ],
            )

        # Unilateral extension at counterparty's sole discretion
        has_unilateral_extension = bool(re.search(
            r"\b(?:client|counterparty|company|customer)\s+[^.\n]*?\b(?:sole\s+option|unilateral\s+right|sole\s+discretion|exclusive\s+option|sole\s+right)\b[^.\n]*?\b(?:to\s+)?(?:extend|renew)\b|"
            r"\b(?:sole\s+option|unilateral\s+right|sole\s+discretion|exclusive\s+option|sole\s+right)\b[^.\n]*?\b(?:to\s+)?(?:extend|renew)\b|"
            r"\b(?:extend|renew)[^.\n]*?\bwithout\s+(?:requiring\s+)?(?:contractor(?:'s)?\s+)?consent\b",
            body_lower,
            re.IGNORECASE,
        ))
        if has_unilateral_extension:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="HIGH",
                unfairness_score=80,
                plain_summary="Grants counterparty the unilateral right or option to extend the term without contractor consent.",
                suggested_pushback="Any extension or renewal of the term shall require the mutual written agreement of both parties.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: forced continuation of obligations upon counterparty demand",
                    "Meaningful imbalance: counterparty retains unilateral extension authority",
                ],
            )

        # Rate freeze across extended terms
        has_rate_freeze = bool(re.search(
            r"\b(?:rates?|fees?|pricing)\s+(?:shall\s+remain\s+fixed|frozen|unadjusted|cannot\s+be\s+increased)\b",
            body_lower,
            re.IGNORECASE,
        )) and any(k in body_lower for k in ["extend", "extension", "renewal", "successive"])
        if has_rate_freeze:
            return HeuristicAssessment(
                category="PAYMENT_TERMS",
                risk_level="MEDIUM",
                unfairness_score=55,
                plain_summary="Freezes rates or fees during extended terms without allowing contractor cost-of-living or inflation adjustments.",
                suggested_pushback="Contractor rates shall be subject to annual adjustment upon mutual written agreement or in accordance with published rate cards.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: rates locked without inflation or cost adjustments",
                    "Meaningful imbalance: unilateral fee restriction",
                ],
            )

        # Standard neutral initial term duration
        return HeuristicAssessment(
            category="OTHER",
            risk_level="LOW",
            unfairness_score=15,
            plain_summary="Standard initial term duration provision defining the effective operational period of the agreement.",
            suggested_pushback=None,
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=[],
        )

    def _evaluate_renewal(
        self,
        body_lower: str,
        is_reciprocal: bool,
        mitigation: dict,
        clause_kind: str,
    ) -> HeuristicAssessment:
        """Evaluates contract renewal provisions.
        Classifies risk only when the substantive body contains real material imbalance.
        """
        # Unilateral renewal power
        has_unilateral_renewal = bool(re.search(
            r"\b(?:client|counterparty|company|customer)\s+[^.\n]*?\b(?:sole\s+option|unilateral\s+right|sole\s+discretion|exclusive\s+option|sole\s+right)\b[^.\n]*?\b(?:to\s+)?(?:renew|extend)\b|"
            r"\b(?:sole\s+option|unilateral\s+right|sole\s+discretion|exclusive\s+option|sole\s+right)\b[^.\n]*?\b(?:to\s+)?(?:renew|extend)\b|"
            r"\b(?:renew|extend)[^.\n]*?\bwithout\s+(?:requiring\s+)?(?:contractor(?:'s)?\s+)?consent\b",
            body_lower,
            re.IGNORECASE,
        ))
        if has_unilateral_renewal:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="HIGH",
                unfairness_score=80,
                plain_summary="Grants counterparty the unilateral right or sole option to renew or extend the agreement without contractor consent, creating a forced lock-in.",
                suggested_pushback="Any renewal or extension of the Agreement shall require the mutual written agreement of both parties executed prior to the expiration of the then-current term.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: unilateral obligation to continue performance upon counterparty demand",
                    "Meaningful imbalance: counterparty retains sole renewal discretion without mutual consent",
                    "Insufficient mitigation: contractor cannot refuse renewal or terminate without penalty",
                ],
            )

        # Forfeiture upon non-renewal / expiration
        has_forfeiture = any(k in body_lower for k in ["without payment for work", "forfeit", "no compensation", "relinquish all claims"])
        if has_forfeiture:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="HIGH",
                unfairness_score=85,
                plain_summary="Imposes forfeiture of compensation or deliverables upon expiration or non-renewal of the contract.",
                suggested_pushback="Upon non-renewal or expiration, Client shall promptly pay Contractor for all Services performed and Deliverables delivered through the expiration date.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: loss of compensation for completed work upon expiration",
                    "Meaningful imbalance: forfeiture penalty tied to contract expiration",
                ],
            )

        # Automatic lock-in / excessive notice window / asymmetric notice
        has_excessive_notice = (
            bool(re.search(
                r"\b(?:60|90|120|180|sixty|ninety|one\s+hundred\s+(?:and\s+)?twenty)\s*(?:\(\d+\)\s*)?(?:days?|business\s+days?)\b",
                body_lower,
                re.IGNORECASE,
            ))
            and any(k in body_lower for k in ["notice", "written notice"])
            and any(k in body_lower for k in ["auto", "automatic", "successive", "renew", "rollover"])
        )
        is_unilateral_notice = bool(re.search(r"\bcontractor\s+(?:must|shall)\s+(?:provide|give)\s+notice\b", body_lower)) and not is_reciprocal

        if has_excessive_notice or is_unilateral_notice:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="MEDIUM",
                unfairness_score=55,
                plain_summary="Automatic renewal provision imposing an excessive notice period (60+ days) or asymmetric burden to prevent contract rollover.",
                suggested_pushback="Renewal shall occur only upon mutual written agreement, or either party may opt out of auto-renewal with at least thirty (30) days prior written notice.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: automatic evergreen rollover locks in obligations",
                    "Meaningful imbalance: excessive or asymmetric notice window required to prevent renewal",
                ],
            )

        # Customary / mutual renewal
        return HeuristicAssessment(
            category="TERMINATION",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Customary mutual renewal provision permitting either party to prevent renewal with standard prior written notice.",
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

        # Unilateral termination for convenience without forfeiture
        is_unilateral_convenience = bool(re.search(
            r"\b(?:client|company|customer)\s+may\s+terminate\s+(?:for\s+convenience|without\s+cause)\b",
            body_lower,
            re.IGNORECASE,
        )) and not is_reciprocal

        if is_unilateral_convenience:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="MEDIUM",
                unfairness_score=50,
                plain_summary="Grants client unilateral termination for convenience rights without reciprocal rights for contractor.",
                suggested_pushback="Either party may terminate for convenience upon thirty (30) days prior written notice.",
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[
                    "Material consequence: unilateral engagement termination",
                    "Meaningful imbalance: client-only termination for convenience",
                ],
            )

        # Mutual or standard termination (reciprocal, breach with cure, or bilateral)
        is_mutual_or_standard = (
            is_reciprocal
            or any(k in body_lower for k in [
                "either party may terminate upon", "either party may terminate",
                "both parties", "non-breaching party", "party not in breach",
                "each party", "mutual written agreement", "neither party may terminate",
            ])
            or mitigation["has_cure_period"]
        )

        if is_mutual_or_standard:
            return HeuristicAssessment(
                category="TERMINATION",
                risk_level="LOW",
                unfairness_score=20,
                plain_summary="Mutual termination clause allowing either party to end the engagement with customary prior written notice or cure period.",
                suggested_pushback=None,
                clause_kind=clause_kind,
                is_risk_bearing=True,
                risk_reasons=[],
            )

        return HeuristicAssessment(
            category="TERMINATION",
            risk_level="LOW",
            unfairness_score=20,
            plain_summary="Standard termination provision with customary notice and remedy procedures.",
            suggested_pushback=None,
            clause_kind=clause_kind,
            is_risk_bearing=True,
            risk_reasons=[],
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

    # =========================================================================
    # Triple-Gate Validation
    # =========================================================================

    def passes_triple_gate(
        self,
        title: str,
        text: str,
        assessment: Optional[HeuristicAssessment] = None,
    ) -> bool:
        """Determines whether a clause satisfies all 3 gates for HIGH risk:
        Gate 1: Material consequence (substantive legal/financial exposure)
        Gate 2: Meaningful imbalance/asymmetry (unilateral, uncapped, unconditional)
        Gate 3: Insufficient mitigation (no caps, no mutuality, no cure period)

        All three gates must be satisfied for a clause to be legitimately HIGH risk.
        """
        full_text = f"{title}\n{text}".strip()
        body_lower = text.lower()

        # Gate 1: Material consequence
        has_material_consequence = bool(
            self.RE_OPERATIVE_TRAP.search(full_text)
            or any(k in body_lower for k in [
                "indemn", "hold harmless", "defend and hold",
                "irrevocably assign", "work made for hire", "immediately upon creation",
                "uncapped", "without limitation or cap",
                "forfeit", "forfeiture",
                "waive all claims", "waives all rights",
                "supersede", "prevail over this agreement",
                "sole option", "unilateral right", "sole discretion to extend",
                "sole option to extend", "unilaterally renew", "unilaterally extend",
            ])
            or (any(k in body_lower for k in ["renew", "renewal", "extend"]) and any(k in body_lower for k in ["sole option", "unilateral", "sole discretion", "without contractor", "without requiring"]))
            or (any(k in body_lower for k in ["terminate", "termination"]) and any(k in body_lower for k in ["immediate", "forfeiture", "without notice"]))
            or (any(k in body_lower for k in ["invoice", "payment"]) and any(k in body_lower for k in ["net 90", "net-90", "withhold all", "unilateral setoff"]))
        )
        if not has_material_consequence:
            return False

        # Gate 2: Meaningful imbalance
        is_reciprocal = bool(self.RE_RECIPROCAL.search(body_lower))
        is_unilateral = bool(re.search(
            r"\b(?:contractor\s+shall|tenant\s+shall|client\s+may|landlord\s+may|solely\s+by|sole\s+discretion|"
            r"unilateral|without\s+contractor|without\s+tenant|at\s+client's\s+option)\b",
            body_lower, re.IGNORECASE
        )) or not is_reciprocal
        if not is_unilateral:
            return False

        # Gate 3: Insufficient mitigation
        mitigation = self._check_mitigation(body_lower)
        if mitigation["has_cap"] or mitigation["has_mutuality"]:
            return False
        if "assign" in body_lower and mitigation["has_condition"]:
            return False
        if ("terminate" in body_lower or "termination" in body_lower) and mitigation["has_cure_period"]:
            return False

        return True


heuristic_engine = HeuristicEngine()


def resolve_referenced_clauses(
    current_clause: Any,
    all_clauses: Optional[List[Any]] = None,
    precomputed_index: Optional[Dict[str, Any]] = None,
) -> List[ResolvedReference]:
    """Module-level convenience wrapper for heuristic_engine.resolve_referenced_clauses."""
    return heuristic_engine.resolve_referenced_clauses(current_clause, all_clauses, precomputed_index=precomputed_index)


def passes_triple_gate(title: str, text: str, assessment: Optional[HeuristicAssessment] = None) -> bool:
    """Module-level convenience wrapper for heuristic_engine.passes_triple_gate."""
    return heuristic_engine.passes_triple_gate(title, text, assessment)
