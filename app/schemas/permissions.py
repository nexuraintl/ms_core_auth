
from pydantic import BaseModel, Field


class PermissionsResponse(BaseModel):
    client_id: int
    uid: int
    modulo: str
    total: int
    permissions: list[str] = Field(default_factory=list)
