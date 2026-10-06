"""Add admin accountability fields (assigned_admin_id, resolved_by_admin_id, status history note).

Revision ID: auth_002
Revises: auth_001
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "auth_002"
down_revision = "auth_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add assigned_admin_id and resolved_by_admin_id to reports
    op.add_column("reports", sa.Column("assigned_admin_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("reports", sa.Column("resolved_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_reports_assigned_admin_id_users",
        "reports",
        "users",
        ["assigned_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_reports_resolved_by_admin_id_users",
        "reports",
        "users",
        ["resolved_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_reports_assigned_admin_id", "reports", ["assigned_admin_id"])
    op.create_index("ix_reports_resolved_by_admin_id", "reports", ["resolved_by_admin_id"])

    # Add optional note to report_status_history
    op.add_column("report_status_history", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("report_status_history", "note")
    op.drop_index("ix_reports_resolved_by_admin_id", table_name="reports")
    op.drop_index("ix_reports_assigned_admin_id", table_name="reports")
    op.drop_constraint("fk_reports_resolved_by_admin_id_users", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_assigned_admin_id_users", "reports", type_="foreignkey")
    op.drop_column("reports", "resolved_by_admin_id")
    op.drop_column("reports", "assigned_admin_id")
