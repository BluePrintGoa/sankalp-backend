from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_csrf, require_roles
from app.database import get_db
from app.models import Appointment, User
from app.schemas.appointment import AppointmentOut, AppointmentUpdate
from app.services.lookup import get_appointment
from app.services.serializers import appointment_data

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/mine", response_model=list[AppointmentOut])
async def patient_appointments(
    user: User = Depends(require_roles("patient")),
    db: AsyncSession = Depends(get_db),
):
    if user.patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    appointments = (
        await db.scalars(
            select(Appointment)
            .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
            .where(Appointment.patient_id == user.patient.id)
            .order_by(Appointment.appointment_date, Appointment.time)
        )
    ).all()
    return [appointment_data(item) for item in appointments]


@router.get("/daily", response_model=list[AppointmentOut])
async def daily_appointments(
    appointment_date: date | None = Query(default=None, alias="date"),
    user: User = Depends(require_roles("doctor")),
    db: AsyncSession = Depends(get_db),
):
    if user.doctor is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    day = appointment_date or date.today()
    appointments = (
        await db.scalars(
            select(Appointment)
            .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
            .where(Appointment.doctor_id == user.doctor.id, Appointment.appointment_date == day)
            .order_by(Appointment.time)
        )
    ).all()
    return [appointment_data(item) for item in appointments]


@router.patch("/{appointment_id}", response_model=AppointmentOut, dependencies=[Depends(require_csrf)])
async def update_appointment(
    appointment_id: str,
    changes: AppointmentUpdate,
    user: User = Depends(require_roles("doctor")),
    db: AsyncSession = Depends(get_db),
):
    appointment = await get_appointment(db, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if user.doctor is None or appointment.doctor_id != user.doctor.id:
        raise HTTPException(status_code=403, detail="Appointment belongs to another doctor")
    fields = changes.model_dump(exclude_unset=True)
    if "date" in fields:
        fields["appointment_date"] = fields.pop("date")
    if fields.get("status"):
        fields["status"] = fields["status"].lower().replace(" ", "_")
    for field, value in fields.items():
        setattr(appointment, field, value)
    await db.commit()
    await db.refresh(appointment)
    appointment = await db.scalar(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
        .where(Appointment.id == appointment.id)
    )
    return appointment_data(appointment)
