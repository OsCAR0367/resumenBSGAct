from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.workflow_schema import BigWorkflowRequest, BigWorkflowResponse
from app.services.big_workflow_service import BigWorkflowService
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository

router = APIRouter(tags=["Workflow"])

@router.post("/big-workflow/test-summary", response_model=BigWorkflowResponse)
async def run_workflow_up_to_summary(
    request: BigWorkflowRequest,
    db: Session = Depends(get_db)
):
    """
    Ejecuta el flujo de procesamiento: Video -> Audio -> Transcripción -> Resumen.
    Retorna el resumen generado. Ideal para pruebas de integración.
    """
    try:

        repo = ProcesamientoRepository(db)
        
        # Convertimos Pydantic a dict
        data = request.dict()
        
        # Insertar Sesión (esto es rápido, se puede dejar directo o envolver)
        sesion_id = await repo.create_sesion_online(data)
        
        # 2. Instanciar e invocar Orquestador
        service = BigWorkflowService(db)
        result = await service.orchestrate_up_to_summary(sesion_id, data)
        
        return BigWorkflowResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))