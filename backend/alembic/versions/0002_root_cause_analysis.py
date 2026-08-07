"""add structured root_cause_analysis to runs

Revision ID: 0002_root_cause_analysis
Revises: 0001_initial
Create Date: 2026-08-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_root_cause_analysis"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("root_cause_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "root_cause_analysis")
