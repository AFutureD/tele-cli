from pathlib import Path

from pydantic import (
    BaseModel,
    Field
)

class SessionInfo(BaseModel):
    session_name: str = Field(...)
    user_id: int = Field(...)
    user_name: str = Field(...)
    user_phone: int = Field(...)
    user_display_name: str = Field(...)
