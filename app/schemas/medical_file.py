from datetime import datetime

from app.schemas.common import APIModel


class MedicalFileOut(APIModel):
    id: str
    name: str
    type: str
    size: int
    url: str
    added_at: datetime
