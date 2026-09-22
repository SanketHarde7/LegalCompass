from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ContractContextPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    filename: Optional[str] = None
    overall_fairness_score: Optional[int] = Field(default=None, alias="overallFairnessScore")
    total_pages: Optional[int] = Field(default=None, alias="totalPages")
    clauses: Optional[List[Dict[str, Any]]] = None


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="Active session UUID")
    message: str = Field(description="User prompt or legal inquiry")
    selected_clause_id: Optional[str] = Field(
        default=None, alias="selectedClauseId", description="Optional specific clause context"
    )
    history: Optional[List[HistoryTurn]] = Field(
        default=None, description="Prior conversational turns"
    )
    contract_context: Optional[ContractContextPayload] = Field(
        default=None, alias="contractContext", description="Document metadata & clauses context"
    )


class TokenChunk(BaseModel):
    type: Literal["token"] = "token"
    content: str


class CitationChunk(BaseModel):
    type: Literal["citation"] = "citation"
    clause_ids: List[str]


class SuggestionChunk(BaseModel):
    type: Literal["suggestion"] = "suggestion"
    target_clause_id: str
    counter_clause: str
    rationale: str


class DoneChunk(BaseModel):
    type: Literal["done"] = "done"
    total_tokens: Optional[int] = None


class ErrorChunk(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: str


SSEStreamChunk = Union[TokenChunk, CitationChunk, SuggestionChunk, DoneChunk, ErrorChunk]


class ChatMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str
    triggered_clause_ids: Optional[List[str]] = Field(default=None, alias="triggeredClauseIds")
    counter_proposal: Optional[str] = Field(default=None, alias="counterProposal")
    scenario_outcome: Optional[Dict[str, Any]] = Field(default=None, alias="scenarioOutcome")
