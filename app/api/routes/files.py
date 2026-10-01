from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_csrf, require_roles
from app.database import get_db
from app.models import MedicalFile, Patient, User
from app.schemas.medical_file import MedicalFileOut
from app.services.file_service import ensure_patient_access, medical_file_data, safe_storage_path, store_upload
from app.services.lookup import get_file, get_patient

router = APIRouter(prefix="/patients", tags=["medical files"])


@router.get("/{patient_id}/files", response_model=list[MedicalFileOut])
async def list_files(
    patient_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    ensure_patient_access(user, patient)
    files = (
        await db.scalars(
            select(MedicalFile)
            .options(selectinload(MedicalFile.patient))
            .where(MedicalFile.patient_id == patient.id)
            .order_by(MedicalFile.created_at.desc())
        )
    ).all()
    return [medical_file_data(file) for file in files]


@router.post("/{patient_id}/files", response_model=MedicalFileOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
async def upload_file(
    patient_id: str,
    file: UploadFile = File(...),
    user: User = Depends(require_roles("doctor")),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    stored = await store_upload(db, patient, user, file)
    stored = await db.scalar(
        select(MedicalFile).options(selectinload(MedicalFile.patient)).where(MedicalFile.id == stored.id)
    )
    return medical_file_data(stored)


@router.delete("/{patient_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def delete_file(
    patient_id: str,
    file_id: str,
    _: User = Depends(require_roles("doctor")),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient(db, patient_id)
    medical_file = await get_file(db, file_id)
    if patient is None or medical_file is None or medical_file.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="File not found")
    path = safe_storage_path(medical_file.storage_path)
    path.unlink(missing_ok=True)
    await db.execute(
        update(Patient)
        .where(Patient.id == patient.id)
        .values(
            storage_used_bytes=case(
                (Patient.storage_used_bytes >= medical_file.size_bytes, Patient.storage_used_bytes - medical_file.size_bytes),
                else_=0,
            )
        )
    )
    await db.delete(medical_file)
    await db.commit()


@router.get("/{patient_id}/files/{file_id}/download")
async def download_file(
    patient_id: str,
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient(db, patient_id)
    medical_file = await get_file(db, file_id)
    if patient is None or medical_file is None or medical_file.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="File not found")
    ensure_patient_access(user, patient)
    path = safe_storage_path(medical_file.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path, media_type=medical_file.content_type, filename=medical_file.filename)
