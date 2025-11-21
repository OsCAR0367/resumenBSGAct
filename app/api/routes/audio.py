from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.audio_service import AudioService
from app.schemas.audio_schema import AudioExtractionRequest, AudioResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Audio"])

@router.post("/extract", summary="Extract Audio from Video", response_model=AudioResponse)
async def extract_audio_endpoint(
    request: AudioExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Extrae audio de un video
    """
    try:
        audio_service = AudioService(db)
        result = await audio_service.extract_audio(
            video_path=request.video_path,
            output_directory=request.output_directory
        )
        return result
    except Exception as e:
        logger.error(f"Error al extraer audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))