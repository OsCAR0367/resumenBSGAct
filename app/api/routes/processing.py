from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_db
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
from app.schemas.processing_schema import (
    SesionOnlineCreate,
    SesionOnlineResponse,
    TipoGenerarCreate,
    TipoGenerarResponse
)
from app.core.logging_config import logger

router = APIRouter()


@router.post("/procesamiento/sesion-online/", response_model=SesionOnlineResponse)
def create_sesion_online(data: SesionOnlineCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva sesión online
    """
    try:
        repo = ProcesamientoRepository(db)
        sesion_online = repo.create_sesion_online(data.dict())
        return sesion_online
    except Exception as e:
        logger.error(f"Error al crear sesión online: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/procesamiento/sesion-online/", response_model=List[SesionOnlineResponse])
def list_sesiones_online(db: Session = Depends(get_db)):
    """
    Lista todas las sesiones online
    """
    try:
        repo = ProcesamientoRepository(db)
        return repo.get_all_sesiones_online()
    except Exception as e:
        logger.error(f"Error al listar sesiones online: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/procesamiento/tipo-generar/", response_model=TipoGenerarResponse)
def create_tipo_generar(data: TipoGenerarCreate, db: Session = Depends(get_db)):
    """
    Registra un tipo de contenido generado
    """
    try:
        repo = ProcesamientoRepository(db)
        
        # Verificar que exista la sesión relacionada
        if not repo.sesion_exists(data.id_procesamiento_sesion_online):
            raise HTTPException(status_code=404, detail="Session not found")
        
        tipo_generar = repo.create_tipo_generar(data.dict())
        return tipo_generar
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear tipo generar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/procesamiento/tipo-generar/{session_id}", response_model=List[TipoGenerarResponse])
def list_tipos_generar(session_id: int, db: Session = Depends(get_db)):
    """
    Lista todos los tipos generados para una sesión específica
    """
    try:
        repo = ProcesamientoRepository(db)
        return repo.get_tipos_generar_by_session(session_id)
    except Exception as e:
        logger.error(f"Error al listar tipos generar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))