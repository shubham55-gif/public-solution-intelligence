"""Create the initial Public Solution Intelligence core schema.

Revision ID: 20260912_0001
Revises: None
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260912_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role = postgresql.ENUM("citizen", "authority", name="user_role", create_type=False)
report_status = postgresql.ENUM(
    "pending", "in_progress", "resolved", name="report_status", create_type=False
)
vlm_validation_status = postgresql.ENUM(
    "pending", "validated", "needs_review", name="vlm_validation_status", create_type=False
)
hotspot_risk_level = postgresql.ENUM(
    "low", "moderate", "high", "critical", name="hotspot_risk_level", create_type=False
)
hotspot_trend = postgresql.ENUM(
    "improving", "stable", "increasing", name="hotspot_trend", create_type=False
)
intervention_status = postgresql.ENUM(
    "planned", "in_progress", "completed", name="intervention_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        user_role,
        report_status,
        vlm_validation_status,
        hotspot_risk_level,
        hotspot_trend,
        intervention_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default=sa.text("'citizen'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("status", report_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("image_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_reports_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_reports_longitude_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_issue_category", "reports", ["issue_category"])
    op.create_index("ix_reports_latitude", "reports", ["latitude"])
    op.create_index("ix_reports_longitude", "reports", ["longitude"])
    op.create_index("ix_reports_latitude_longitude", "reports", ["latitude", "longitude"])
    op.create_index("ix_reports_reported_at", "reports", ["reported_at"])
    op.create_index("ix_reports_status", "reports", ["status"])

    op.create_table(
        "ai_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("llm_output", sa.Text(), nullable=True),
        sa.Column("extracted_category", sa.String(length=100), nullable=True),
        sa.Column("time_context", sa.String(length=255), nullable=True),
        sa.Column("severity_indicator", sa.String(length=50), nullable=True),
        sa.Column("vlm_result", sa.Text(), nullable=True),
        sa.Column(
            "vlm_validation_status",
            vlm_validation_status,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("report_id", name="uq_ai_analysis_report_id"),
    )

    op.create_table(
        "hotspots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("center_latitude", sa.Float(), nullable=False),
        sa.Column("center_longitude", sa.Float(), nullable=False),
        sa.Column("report_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("dominant_category", sa.String(length=100), nullable=True),
        sa.Column("risk_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("risk_level", hotspot_risk_level, nullable=False, server_default=sa.text("'low'")),
        sa.Column("trend", hotspot_trend, nullable=False, server_default=sa.text("'stable'")),
        sa.Column("peak_time_start", sa.Time(), nullable=True),
        sa.Column("peak_time_end", sa.Time(), nullable=True),
        sa.Column("recurrence_level", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("center_latitude BETWEEN -90 AND 90", name="ck_hotspots_latitude_range"),
        sa.CheckConstraint("center_longitude BETWEEN -180 AND 180", name="ck_hotspots_longitude_range"),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_hotspots_risk_score_range"),
    )
    op.create_index("ix_hotspots_risk_score", "hotspots", ["risk_score"])
    op.create_index("ix_hotspots_trend", "hotspots", ["trend"])

    op.create_table(
        "hotspot_reports",
        sa.Column("hotspot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("hotspot_id", "report_id", name="pk_hotspot_reports"),
    )

    op.create_table(
        "interventions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("hotspot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_unit", sa.String(length=255), nullable=True),
        sa.Column(
            "status", intervention_status, nullable=False, server_default=sa.text("'planned'")
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_interventions_hotspot_id", "interventions", ["hotspot_id"])
    op.create_index("ix_interventions_status", "interventions", ["status"])

    op.create_table(
        "impact_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("hotspot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervention_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_risk_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("after_risk_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("before_report_frequency", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("after_report_frequency", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("before_recurrence_level", sa.String(length=50), nullable=True),
        sa.Column("after_recurrence_level", sa.String(length=50), nullable=True),
        sa.Column("risk_reduction_percent", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("report_reduction_percent", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["intervention_id"], ["interventions.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_impact_metrics_hotspot_id", "impact_metrics", ["hotspot_id"])
    op.create_index("ix_impact_metrics_intervention_id", "impact_metrics", ["intervention_id"])

    op.create_table(
        "report_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_status", report_status, nullable=False),
        sa.Column("new_status", report_status, nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_report_status_history_report_id", "report_status_history", ["report_id"])
    op.create_index("ix_report_status_history_changed_by", "report_status_history", ["changed_by"])


def downgrade() -> None:
    op.drop_index("ix_report_status_history_changed_by", table_name="report_status_history")
    op.drop_index("ix_report_status_history_report_id", table_name="report_status_history")
    op.drop_table("report_status_history")
    op.drop_index("ix_impact_metrics_intervention_id", table_name="impact_metrics")
    op.drop_index("ix_impact_metrics_hotspot_id", table_name="impact_metrics")
    op.drop_table("impact_metrics")
    op.drop_index("ix_interventions_status", table_name="interventions")
    op.drop_index("ix_interventions_hotspot_id", table_name="interventions")
    op.drop_table("interventions")
    op.drop_table("hotspot_reports")
    op.drop_index("ix_hotspots_trend", table_name="hotspots")
    op.drop_index("ix_hotspots_risk_score", table_name="hotspots")
    op.drop_table("hotspots")
    op.drop_table("ai_analysis")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_reported_at", table_name="reports")
    op.drop_index("ix_reports_latitude_longitude", table_name="reports")
    op.drop_index("ix_reports_longitude", table_name="reports")
    op.drop_index("ix_reports_latitude", table_name="reports")
    op.drop_index("ix_reports_issue_category", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in (
        intervention_status,
        hotspot_trend,
        hotspot_risk_level,
        vlm_validation_status,
        report_status,
        user_role,
    ):
        enum_type.drop(bind, checkfirst=True)
