from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.modules.branches.repository import BranchesRepository
from app.schemas.branch import BranchCreate


class BranchesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BranchesRepository(db)

    def list_branches(self) -> list[Branch]:
        return self.repository.list_branches()

    def create_branch(self, payload: BranchCreate, actor_id) -> Branch:
        branch = Branch(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        self.repository.create_branch(branch)
        self.db.commit()
        self.db.refresh(branch)
        return branch

