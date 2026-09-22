from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ApiErrorDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="User-friendly description")
    details: Optional[Dict[str, Any]] = Field(default=None)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: Optional[str] = Field(default=None, alias="requestId")


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    error: ApiErrorDetail
