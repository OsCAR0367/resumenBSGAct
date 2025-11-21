from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.azure_transcription_service import AzureTranscriptionService
from app.schemas.transcription_schema import TranscriptionRequest, TranscriptionResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Transcription"])


@router.post("/transcribe", summary="Transcribe Audio", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(
    request: TranscriptionRequest,
    db: Session = Depends(get_db)
):
    """
    Transcribe un archivo de audio a texto
    """
    try:
        transcription_service = AzureTranscriptionService(db)
        result = await transcription_service.transcribe(
            audio_path=request.audio_path,
            output_directory=request.output_directory
        )
        return result
    except Exception as e:
        logger.error(f"Error al transcribir audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))