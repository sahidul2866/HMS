"""HR & Payroll Management Module"""

from app.modules.hr.router import router
from app.modules.hr.service import HRService

__all__ = ["router", "HRService"]
