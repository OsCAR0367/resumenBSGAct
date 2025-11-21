from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.study_guide_service import StudyGuideService
from app.schemas.study_guide_schema import StudyGuideRequest, StudyGuideResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Study Guide"])


@router.post("/generate", summary="Generate Study Guide", response_model=StudyGuideResponse)
async def generate_study_guide_endpoint(
    request: StudyGuideRequest,
    db: Session = Depends(get_db)
):
    """
    Genera una guía de estudio en formato PDF
    """
    try:
        study_guide_service = StudyGuideService(db)
        result = await study_guide_service.generate_study_guide(
            summary_path=request.summary_path,
            output_directory=request.output_directory
        )
        return result
    except Exception as e:
        logger.error(f"Error al generar guía de estudio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))