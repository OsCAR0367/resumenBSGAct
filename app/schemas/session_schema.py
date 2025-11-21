from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    correo: str
    area: str


class SessionResponse(BaseModel):
    id: int
    correo: str
    area: str
    fecha_creacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True