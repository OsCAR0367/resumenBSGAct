from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.podcast_service import PodcastService
from app.schemas.podcast_schema import PodcastRequest, PodcastResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Podcast"])


@router.post("/generate-podcast", summary="Generate Podcast from Summary", response_model=PodcastResponse)
async def generate_podcast_endpoint(
    request: PodcastRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un podcast en formato de audio desde un resumen
    """
    try:
        podcast_service = PodcastService(db)
        result = await podcast_service.generate_podcast(
            summary_file=request.summary_file,
            audio_output=request.audio_output,
            script_output=request.script_output
        )
        return result
    except Exception as e:
        logger.error(f"Error al generar podcast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))