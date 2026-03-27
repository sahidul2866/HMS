from pydantic import BaseModel


class LaboratorySummaryRead(BaseModel):
    total_orders: int
    pending_orders: int
    collected_orders: int
    in_progress_orders: int
    completed_orders: int
    verified_orders: int
