from pydantic import BaseModel
from typing import Any, Optional


class SessionResponse(BaseModel):
    authenticated: bool
    session_id: Optional[str] = None
    user: Optional[dict[str, Any]] = None