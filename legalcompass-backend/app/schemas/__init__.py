"""Pydantic schemas for LegalCompass API."""
from .contract import (
    RiskLevel,
    RiskCategory,
    Clause,
    ContractDocument,
    UploadContractResponse,
)
from .chat import ChatStreamRequest, SSEStreamChunk, ChatMessage
from .simulate import (
    SimulateScenarioRequest,
    ScenarioSimulationResult,
    TriggeredClauseItem,
)
from .error import ApiErrorResponse

__all__ = [
    "RiskLevel",
    "RiskCategory",
    "Clause",
    "ContractDocument",
    "UploadContractResponse",
    "ChatStreamRequest",
    "SSEStreamChunk",
    "ChatMessage",
    "SimulateScenarioRequest",
    "ScenarioSimulationResult",
    "TriggeredClauseItem",
    "ApiErrorResponse",
]
