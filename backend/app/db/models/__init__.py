"""Import every model module so Base.metadata is fully populated for Alembic autogenerate."""
from app.db.models.credential import CredentialProfile
from app.db.models.knowledge import KnowledgeSource
from app.db.models.project import Project
from app.db.models.report import Report
from app.db.models.requirement import Requirement
from app.db.models.run import Evidence, Run, Step
from app.db.models.user import User

__all__ = [
    "CredentialProfile",
    "KnowledgeSource",
    "Project",
    "Report",
    "Requirement",
    "Evidence",
    "Run",
    "Step",
    "User",
]
