import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, Doctor, MedicalFile, Patient


def id_filter(model, identifier: str):
    conditions = [model.public_id == identifier]
    try:
        conditions.append(model.id == uuid.UUID(identifier))
    except ValueError:
        pass
    return conditions


async def get_patient(db: AsyncSession, identifier: str) -> Patient | None:
    return await db.scalar(select(Patient).where(or_(*id_filter(Patient, identifier))))


async def get_doctor(db: AsyncSession, identifier: str) -> Doctor | None:
    return await db.scalar(select(Doctor).where(or_(*id_filter(Doctor, identifier))))


async def get_appointment(db: AsyncSession, identifier: str) -> Appointment | None:
    return await db.scalar(select(Appointment).where(or_(*id_filter(Appointment, identifier))))


async def get_file(db: AsyncSession, identifier: str) -> MedicalFile | None:
    try:
        file_uuid = uuid.UUID(identifier)
    except ValueError:
        return None
    return await db.get(MedicalFile, file_uuid)
