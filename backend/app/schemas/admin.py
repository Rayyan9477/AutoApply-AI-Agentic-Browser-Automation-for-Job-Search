"""Admin/health schemas (superuser-only views)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SystemIssueResponse(BaseModel):
    """A harness-detected workflow/system anomaly."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    category: str
    severity: str
    signals: dict[str, Any]
    diagnosis: str
    status: str
    detected_at: datetime
    created_at: datetime
