from uuid import UUID

from pydantic import BaseModel


class PermissionRead(BaseModel):
    id: UUID
    code: str
    module: str
    action: str
    description: str | None = None

    model_config = {"from_attributes": True}

