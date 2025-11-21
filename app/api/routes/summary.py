from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.summarization_service import SummarizationService
from app.schemas.summary_schema import SummaryRequest, SummaryResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Summary"])


@router.post("/generate", summary="Generate Summary", response_model=SummaryResponse)
async def generate_summary_endpoint(
    request: SummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un resumen a partir de una transcripción
    """
    try:
        summary_service = SummarizationService(db)
        result = await summary_service.generate_summary(
            transcription_path=request.transcription_path,
            output_directory=request.output_directory
        )
        return result
    except Exception as e:
        logger.error(f"Error al generar resumen: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))