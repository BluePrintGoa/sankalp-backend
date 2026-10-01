from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_csrf, require_roles
from app.database import get_db
from app.models import Patient, User
from app.schemas.patient import PatientOut, PatientUpdate
from app.services.lookup import get_patient
from app.services.serializers import patient_data
from app.utils.qr import patient_qr_svg

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
async def list_patients(
    _: User = Depends(require_roles("doctor")), db: AsyncSession = Depends(get_db)
):
    patients = (await db.scalars(select(Patient).order_by(Patient.name))).all()
    return [patient_data(patient) for patient in patients]


@router.get("/{patient_id}", response_model=PatientOut)
async def patient_detail(
    patient_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    patient = await get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if user.role == "patient" and patient.user_id != user.id:
        raise HTTPException(status_code=403, detail="Patients may only view their own record")
    if user.role not in {"patient", "doctor"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return patient_data(patient)


@router.patch("/{patient_id}", response_model=PatientOut, dependencies=[Depends(require_csrf)])
async def update_patient(
    patient_id: str,
    changes: PatientUpdate,
    _: User = Depends(require_roles("doctor")),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    await db.commit()
    await db.refresh(patient)
    return patient_data(patient)


@router.get("/{patient_id}/qr", responses={200: {"content": {"image/svg+xml": {}}}})
async def patient_qr(
    patient_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    patient = await get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if user.role == "patient" and patient.user_id != user.id:
        raise HTTPException(status_code=403, detail="Patients may only access their own QR code")
    if user.role not in {"patient", "doctor"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return Response(patient_qr_svg(patient.public_id), media_type="image/svg+xml")
