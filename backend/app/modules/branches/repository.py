from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch


class BranchesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_branches(self) -> list[Branch]:
        return list(self.db.scalars(select(Branch).order_by(Branch.name.asc())))

    def create_branch(self, branch: Branch) -> Branch:
        self.db.add(branch)
        self.db.flush()
        return branch

