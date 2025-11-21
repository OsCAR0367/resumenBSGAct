from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SesionOnlineCreate(BaseModel):
    """
    Schema para crear una sesión online
    """
    id_pe_especifico: int
    id_pe_especifico_sesion: Optional[int] = None
    tipo_resumen_grabacion_online: str
    sesion: str
    url_video: str


class SesionOnlineResponse(BaseModel):
    """
    Schema de respuesta para sesión online
    """
    id: int
    id_pe_especifico: int
    id_pe_especifico_sesion: Optional[int] = None
    tipo_resumen_grabacion_online: str
    sesion: str
    url_video: str
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TipoGenerarCreate(BaseModel):
    """
    Schema para crear un tipo de contenido generado
    """
    id_procesamiento_sesion_online: int
    id_resumen_grabacion_online: int
    registro_url: Optional[str] = None


class TipoGenerarResponse(BaseModel):
    """
    Schema de respuesta para tipo generado
    """
    id: int
    id_procesamiento_sesion_online: int
    id_resumen_grabacion_online: int
    registro_url: Optional[str] = None
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True