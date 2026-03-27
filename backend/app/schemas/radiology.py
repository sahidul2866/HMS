from pydantic import BaseModel


class RadiologySummaryRead(BaseModel):
    total_orders: int
    pending_orders: int
    ready_orders: int
    in_progress_orders: int
    completed_orders: int
    verified_orders: int
