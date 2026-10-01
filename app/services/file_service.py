import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import MedicalFile, Patient, User


def ensure_patient_access(user: User, patient: Patient) -> None:
    if user.role == "doctor":
        return
    if user.role != "patient" or patient.user_id != user.id:
        raise HTTPException(status_code=403, detail="You may only access your own patient files")


def medical_file_data(file: MedicalFile) -> dict:
    return {
        "id": str(file.id),
        "name": file.filename,
        "type": file.content_type,
        "size": file.size_bytes,
        "url": f"/patients/{file.patient.public_id}/files/{file.id}/download",
        "added_at": file.created_at,
    }


async def store_upload(
    db: AsyncSession,
    patient: Patient,
    uploaded_by: User,
    upload: UploadFile,
) -> MedicalFile:
    raw_name = Path(upload.filename or "upload").name
    filename = "".join(char for char in raw_name if char.isprintable() and char not in "/\\")[:200].strip(" .")
    filename = filename or "upload"
    stored_name = f"{uuid.uuid4()}_{filename}"
    patient_dir = (settings.upload_dir / patient.public_id).resolve()
    upload_root = settings.upload_dir.resolve()
    if upload_root not in patient_dir.parents and patient_dir != upload_root:
        raise HTTPException(status_code=400, detail="Invalid patient storage path")
    patient_dir.mkdir(parents=True, exist_ok=True)
    destination = patient_dir / stored_name
    size_bytes = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > settings.max_file_storage_bytes:
                    raise HTTPException(status_code=413, detail="File exceeds the patient storage quota")
                output.write(chunk)
        if size_bytes == 0:
            raise HTTPException(status_code=400, detail="Empty files cannot be uploaded")
        relative_path = destination.relative_to(upload_root).as_posix()
        file = MedicalFile(
            patient_id=patient.id,
            filename=filename,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            storage_path=relative_path,
            uploaded_by=uploaded_by.id,
        )
        db.add(file)
        result = await db.execute(
            update(Patient)
            .where(
                Patient.id == patient.id,
                Patient.storage_used_bytes + size_bytes <= settings.max_file_storage_bytes,
            )
            .values(storage_used_bytes=Patient.storage_used_bytes + size_bytes)
        )
        if result.rowcount != 1:
            raise HTTPException(status_code=413, detail="Patient storage quota exceeded")
        await db.commit()
        await db.refresh(file)
        return file
    except Exception:
        await db.rollback()
        destination.unlink(missing_ok=True)
        raise


def safe_storage_path(relative_path: str) -> Path:
    root = settings.upload_dir.resolve()
    path = (root / relative_path).resolve()
    if root not in path.parents:
        raise HTTPException(status_code=404, detail="Stored file not found")
    return path
