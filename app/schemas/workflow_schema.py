from pydantic import BaseModel
from typing import List, Optional

class BigWorkflowRequest(BaseModel):
    """
    Esquema de entrada para iniciar el flujo de procesamiento.
    """
    IdPEspecifico: int
    IdPEspecificoSesion: Optional[int] = None
    TipoResumenGrabacionOnline: List[int] = [] 
    Sesion: str
    UrlVideo: str
    Usuario: str

class BigWorkflowResponse(BaseModel):
    """
    Esquema de respuesta para el endpoint de prueba.
    Devuelve detalles útiles para validar que cada paso funcionó.
    """
    message: str
    sesion_id: int
    status: str
    

    video_path: Optional[str] = None
    transcript_preview: Optional[str] = None  
    summary_preview: Optional[str] = None
    
    pdf_url: Optional[str] = None
    podcast_url: Optional[str] = None