from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

RiskLevel = Literal["HIGH", "MEDIUM", "LOW", "NEUTRAL"]

ClauseKind = Literal["DEFINITION", "HEADING", "RECITAL", "BOILERPLATE", "OPERATIVE"]

RiskCategory = Literal[
    "INDEMNIFICATION",
    "LIABILITY",
    "INTELLECTUAL_PROPERTY",
    "TERMINATION",
    "PAYMENT_TERMS",
    "CONFIDENTIALITY",
    "NON_COMPETE",
    "WARRANTIES",
    "DISPUTE_RESOLUTION",
    "IP_RIGHTS",
    "PAYMENT",
    "DISPUTE",
    "MISC",
    "OTHER",
]


class Clause(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(description="Unique clause identifier, e.g. clause_1")
    index: int = Field(default=1, description="Positional 1-indexed order")
    title: str = Field(description="Extracted or synthesized heading")
    text: str = Field(description="Raw legal verbiage from source document")
    category: str = Field(default="OTHER", description="Categorical classification")
    risk_level: RiskLevel = Field(default="LOW", alias="riskLevel", description="Evaluated severity level")
    plain_english_summary: str = Field(
        default="", alias="plainSummary", description="Translates legalese into plain language"
    )
    suggested_pushback: Optional[str] = Field(
        default=None, alias="suggestion", description="Balanced counter-draft proposal"
    )
    unfairness_score: int = Field(
        default=30, alias="unfairnessScore", description="Unfairness score 0 (fair) to 100 (predatory)"
    )
    clause_kind: str = Field(
        default="OPERATIVE", alias="clauseKind",
        description="Structural classification: DEFINITION, HEADING, RECITAL, BOILERPLATE, OPERATIVE"
    )
    is_risk_bearing: bool = Field(
        default=True, alias="isRiskBearing",
        description="Whether this clause can carry material risk (False for definitions, headings, recitals)"
    )
    risk_reasons: List[str] = Field(
        default_factory=list, alias="riskReasons",
        description="Specific semantic reasons justifying the assigned risk_level"
    )
    page_number: Optional[int] = Field(
        default=1, alias="pageNumber", description="Page number in source PDF if applicable"
    )
    start_offset: Optional[int] = Field(
        default=None, alias="startOffset", description="Character start offset in the page text"
    )
    end_offset: Optional[int] = Field(
        default=None, alias="endOffset", description="Character end offset in the page text"
    )

    @property
    def originalText(self) -> str:
        return self.text

    @property
    def plainSummary(self) -> str:
        return self.plain_english_summary

    @property
    def riskLevel(self) -> str:
        return self.risk_level

    @property
    def unfairnessScore(self) -> int:
        return self.unfairness_score

    @property
    def suggestion(self) -> Optional[str]:
        return self.suggested_pushback

    @property
    def clauseKind(self) -> str:
        return self.clause_kind

    @property
    def isRiskBearing(self) -> bool:
        return self.is_risk_bearing

    @property
    def riskReasons(self) -> List[str]:
        return self.risk_reasons

    @property
    def pageNumber(self) -> Optional[int]:
        return self.page_number

    @property
    def startOffset(self) -> Optional[int]:
        return self.start_offset

    @property
    def endOffset(self) -> Optional[int]:
        return self.end_offset


class PageContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page_number: int = Field(alias="pageNumber", description="1-indexed page number")
    text: str = Field(description="Full text extracted from page")

    @property
    def pageNumber(self) -> int:
        return self.page_number


class ContractDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="Session UUID")
    filename: str = Field(description="Original filename uploaded")
    document_title: Optional[str] = Field(default=None, alias="documentTitle", description="Extracted document title")
    upload_timestamp: str = Field(alias="uploadTimestamp", description="ISO 8601 timestamp")
    overall_fairness_score: int = Field(
        alias="overallFairnessScore", description="Overall fairness score 0 to 100"
    )
    total_pages: int = Field(default=1, alias="totalPages", description="Total pages in document")
    pages: List[PageContent] = Field(default_factory=list, description="Extracted content per page")
    clauses: List[Clause] = Field(default_factory=list, description="List of analyzed clauses")

    @property
    def sessionId(self) -> str:
        return self.session_id

    @property
    def uploadTimestamp(self) -> str:
        return self.upload_timestamp

    @property
    def overallFairnessScore(self) -> int:
        return self.overall_fairness_score

    @property
    def totalPages(self) -> int:
        return self.total_pages

    @property
    def documentTitle(self) -> Optional[str]:
        return self.document_title


class UploadContractResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="UUID identifying the analysis session")
    filename: str = Field(description="Original filename uploaded")
    document_title: Optional[str] = Field(default=None, alias="documentTitle", description="Extracted document title")
    file_size_bytes: int = Field(default=0, description="Size in bytes")
    uploaded_at: str = Field(alias="uploadTimestamp", description="ISO 8601 timestamp")
    total_clauses: int = Field(default=0, description="Count of identified clauses")
    overall_fairness_score: int = Field(
        default=50, alias="overallFairnessScore", description="Overall fairness score 0 to 100"
    )
    total_pages: int = Field(default=1, alias="totalPages", description="Total pages in document")
    pages: List[PageContent] = Field(default_factory=list, description="Extracted content per page")
    summary_overview: str = Field(
        default="", description="High-level executive breakdown"
    )
    clauses: List[Clause] = Field(default_factory=list, description="Array of analyzed clauses")
    document: Optional[ContractDocument] = Field(
        default=None, description="Direct ContractDocument representation for frontend store"
    )
