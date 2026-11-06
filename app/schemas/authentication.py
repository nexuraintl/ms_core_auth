
from pydantic import BaseModel, EmailStr, Field


class AuthenticationRequest(BaseModel):
    client_id: str = Field(..., min_length=1)
    user: EmailStr
    password: str = Field(..., min_length=1)


class AuthenticationResponse(BaseModel):
    authenticated: bool
    access_token: str
    token_type: str = "Bearer"
