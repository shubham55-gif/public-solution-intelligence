"""Database operations for reports, kept separate from HTTP routing."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.entities import (
    Notification,
    Report,
    ReportStatus,
    ReportStatusHistory,
    User,
    UserRole,
)
from app.schemas.reports import ReportCreate, ReportSeverity


class ReportPersistenceError(Exception):
    """Raised after a report transaction has been rolled back."""


class ReportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def user_exists(self, user_id: UUID) -> bool:
        return self.session.get(User, user_id) is not None

    def authority_exists(self, user_id: UUID) -> bool:
        user = self.session.get(User, user_id)
        return user is not None and user.is_admin

    def update_status(
        self, *, report_id: UUID, new_status: ReportStatus, changed_by: UUID
    ) -> Report:
        report = self.session.get(Report, report_id)
        if report is None:
            raise LookupError("Report not found")

        history = ReportStatusHistory(
            report_id=report.id,
            old_status=report.status,
            new_status=new_status,
            changed_by=changed_by,
        )
        report.status = new_status
        if new_status == ReportStatus.IN_PROGRESS or report.assigned_admin_id is None:
            report.assigned_admin_id = changed_by

        report.updated_at = datetime.now(timezone.utc)
        self.session.add(history)

        # Notify the citizen owner with the admin's name
        admin_user = self.session.get(User, changed_by)
        admin_name = admin_user.name if admin_user else "Authorities"

        if new_status == ReportStatus.IN_PROGRESS:
            msg = f"Your report regarding '{report.issue_category}' is now being handled by Admin {admin_name}."
        else:
            msg = f"Your complaint regarding '{report.issue_category}' has been marked as {new_status.value.replace('_', ' ')} by Admin {admin_name}."

        notif = Notification(
            user_id=report.user_id,
            report_id=report.id,
            title=f"Report Status: {new_status.value.replace('_', ' ').title()}",
            message=msg,
            notification_type="status_update",
        )
        self.session.add(notif)

        try:
            self.session.commit()
            self.session.refresh(report)
            return report
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ReportPersistenceError("Could not update report status") from exc

    def resolve_report(
        self,
        *,
        report_id: UUID,
        changed_by: UUID,
        resolution_note: str | None = None,
        resolution_image_path: str | None = None,
    ) -> Report:
        """Set a report to RESOLVED, store resolution note, admin accountability and after-photo path."""
        report = self.session.get(Report, report_id)
        if report is None:
            raise LookupError("Report not found")

        now = datetime.now(timezone.utc)
        history = ReportStatusHistory(
            report_id=report.id,
            old_status=report.status,
            new_status=ReportStatus.RESOLVED,
            changed_by=changed_by,
            note=resolution_note,
        )
        report.status = ReportStatus.RESOLVED
        report.resolution_note = resolution_note
        if resolution_image_path is not None:
            report.resolution_image_path = resolution_image_path
        report.resolved_by_admin_id = changed_by
        if report.assigned_admin_id is None:
            report.assigned_admin_id = changed_by
        report.resolved_at = now
        report.updated_at = now
        self.session.add(history)

        # Notify the citizen owner about resolution
        admin_user = self.session.get(User, changed_by)
        admin_name = admin_user.name if admin_user else "Authorities"
        note_text = f" Resolution notes: {resolution_note}" if resolution_note else ""
        notif = Notification(
            user_id=report.user_id,
            report_id=report.id,
            title="Report Resolved",
            message=f"Your report regarding '{report.issue_category}' has been resolved by Admin {admin_name}.{note_text}",
            notification_type="resolution",
        )
        self.session.add(notif)

        try:
            self.session.commit()
            self.session.refresh(report)
            return report
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ReportPersistenceError("Could not resolve report") from exc

    def create_report(
        self, *, data: ReportCreate, user_id: UUID, image_path: str | None
    ) -> Report:
        report = Report(
            user_id=user_id,
            issue_category=data.issue_category,
            description=data.description,
            latitude=data.latitude,
            longitude=data.longitude,
            reported_at=data.reported_at,
            severity=data.severity.value,
            status=ReportStatus.PENDING,
            image_path=image_path,
        )
        self.session.add(report)
        try:
            self.session.commit()
            self.session.refresh(report)
            return report
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ReportPersistenceError("Could not persist report") from exc

    def get_report(self, report_id: UUID) -> Report | None:
        try:
            statement = (
                select(Report)
                .options(
                    selectinload(Report.ai_analysis),
                    selectinload(Report.user),
                    selectinload(Report.assigned_admin),
                    selectinload(Report.resolved_by_admin),
                    selectinload(Report.status_history).selectinload(ReportStatusHistory.changed_by_user),
                )
                .where(Report.id == report_id)
            )
            return self.session.scalar(statement)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ReportPersistenceError("Could not retrieve report") from exc

    def list_reports(
        self,
        *,
        page: int,
        page_size: int,
        category: str | None = None,
        status: ReportStatus | None = None,
        severity: ReportSeverity | None = None,
        user_id: UUID | None = None,
    ) -> tuple[list[Report], int]:
        conditions = []
        if category:
            conditions.append(Report.issue_category == category)
        if status:
            conditions.append(Report.status == status)
        if severity:
            conditions.append(Report.severity == severity.value)
        if user_id:
            conditions.append(Report.user_id == user_id)

        statement = (
            select(Report)
            .options(
                selectinload(Report.ai_analysis),
                selectinload(Report.user),
                selectinload(Report.assigned_admin),
                selectinload(Report.resolved_by_admin),
                selectinload(Report.status_history).selectinload(ReportStatusHistory.changed_by_user),
            )
            .where(*conditions)
            .order_by(Report.reported_at.desc())
        )
        count_statement = select(func.count()).select_from(Report).where(*conditions)
        try:
            total = self.session.scalar(count_statement) or 0
            reports = list(
                self.session.scalars(statement.offset((page - 1) * page_size).limit(page_size))
            )
            return reports, total
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ReportPersistenceError("Could not retrieve reports") from exc
