"""Database operations for authority interventions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import Hotspot, Intervention, InterventionStatus
from app.schemas.interventions import InterventionCreate, InterventionUpdate


class InterventionPersistenceError(Exception):
    """Raised after an intervention transaction has been rolled back."""


class InterventionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def hotspot_exists(self, hotspot_id: UUID) -> bool:
        return self.session.get(Hotspot, hotspot_id) is not None

    def create(self, data: InterventionCreate) -> Intervention:
        intervention = Intervention(
            hotspot_id=data.hotspot_id,
            action_type=data.action_type,
            description=data.description,
            assigned_unit=data.assigned_unit,
            status=InterventionStatus(data.status.value),
            started_at=data.started_at,
            completed_at=data.completed_at,
        )
        self.session.add(intervention)
        try:
            self.session.commit()
            self.session.refresh(intervention)
            return intervention
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InterventionPersistenceError("Could not create intervention") from exc

    def get(self, intervention_id: UUID) -> Intervention | None:
        try:
            return self.session.get(Intervention, intervention_id)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InterventionPersistenceError("Could not retrieve intervention") from exc

    def list(
        self,
        *,
        page: int,
        page_size: int,
        hotspot_id: UUID | None,
        status: InterventionStatus | None,
    ) -> tuple[list[Intervention], int]:
        conditions = []
        if hotspot_id is not None:
            conditions.append(Intervention.hotspot_id == hotspot_id)
        if status is not None:
            conditions.append(Intervention.status == status)

        statement = (
            select(Intervention)
            .where(*conditions)
            .order_by(Intervention.created_at.desc())
        )
        count_statement = select(func.count()).select_from(Intervention).where(*conditions)
        try:
            total = self.session.scalar(count_statement) or 0
            items = list(
                self.session.scalars(
                    statement.offset((page - 1) * page_size).limit(page_size)
                )
            )
            return items, total
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InterventionPersistenceError("Could not list interventions") from exc

    def update(self, intervention_id: UUID, data: InterventionUpdate) -> Intervention:
        intervention = self.session.get(Intervention, intervention_id)
        if intervention is None:
            raise LookupError("Intervention not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "status" and value is not None:
                value = InterventionStatus(value.value)
            setattr(intervention, field, value)
        intervention.updated_at = datetime.now(timezone.utc)
        try:
            self.session.commit()
            self.session.refresh(intervention)
            return intervention
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InterventionPersistenceError("Could not update intervention") from exc
