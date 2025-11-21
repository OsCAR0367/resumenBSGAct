from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.concept_map_service import ConceptMapService
from app.schemas.concept_map_schema import ConceptMapRequest, ConceptMapResponse
from app.core.logging_config import logger

router = APIRouter(tags=["Concept Map"])


@router.post("/generate-concept-map", summary="Generate Concept Map", response_model=ConceptMapResponse)
async def generate_concept_map_endpoint(
    request: ConceptMapRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un mapa conceptual en formato HTML
    """
    try:
        concept_map_service = ConceptMapService(db)
        result = await concept_map_service.generate_concept_map(
            summary_file=request.summary_file,
            output_path=request.output_path
        )
        return result
    except Exception as e:
        logger.error(f"Error al generar mapa conceptual: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))