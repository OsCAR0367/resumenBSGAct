from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.infrastructure.repositories.session_repository import SessionRepository
from app.schemas.session_schema import SessionCreate, SessionResponse
from app.core.logging_config import logger

router = APIRouter()


@router.post("/sessions/", response_model=SessionResponse)
def create_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva sesión de aviso de procesamiento
    """
    try:
        repo = SessionRepository(db)
        session = repo.create_session(session_data.dict())
        return session
    except Exception as e:
        logger.error(f"Error al crear sesión: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))