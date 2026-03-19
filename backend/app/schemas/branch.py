from uuid import UUID

from pydantic import BaseModel, Field


class BranchCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    address: str | None = None


class BranchRead(BranchCreate):
    id: UUID
    is_active: bool

    model_config = {"from_attributes": True}

