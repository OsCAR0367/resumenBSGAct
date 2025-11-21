from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_db
from app.services.big_workflow_service import BigWorkflowService
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
from app.schemas.workflow_schema import BigWorkflowRequest, BigWorkflowResponse, BigWorkflowBatchResponse
from app.daemons.worker_celery import big_workflow_task
from app.core.logging_config import logger

router = APIRouter(tags=["Workflow"])


@router.post("/big-workflow", response_model=BigWorkflowResponse)
def run_big_workflow(request: BigWorkflowRequest, db: Session = Depends(get_db)):
    """
    Ejecuta el flujo completo de procesamiento de video de forma síncrona
    """
    try:
        # Insert the main record immediately to obtain the session ID.
        procesamiento_repo = ProcesamientoRepository(db)
        sesion_id = procesamiento_repo.create_sesion_online(request.dict())
        
        # Call the orchestrator with the pre-created session ID.
        workflow_service = BigWorkflowService(db)
        result = workflow_service.orchestrate_big_workflow(sesion_id, request.dict())
        
        return BigWorkflowResponse(
            message="Workflow triggered",
            details=result
        )
    except Exception as e:
        logger.error(f"Error en big workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", summary="Run multiple big workflow jobs asynchronously", response_model=BigWorkflowBatchResponse)
def big_workflow_batch_endpoint(
    requests: List[BigWorkflowRequest],
    db: Session = Depends(get_db)
):
    """
    Accepts an array of workflow inputs and queues each one in Celery.
    Returns a list of Celery task IDs.
    """
    try:
        task_ids = []
        procesamiento_repo = ProcesamientoRepository(db)

        for req in requests:
            # 1) Convierte Pydantic model a dict
            data = req.dict()

            # 2) Crea (o recupera) la sesión => no más duplicados
            sesion_id = procesamiento_repo.create_sesion_online(data)
            data["sesion_id"] = sesion_id

            # 3) Encola la Celery task con el data ya actualizado
            result = big_workflow_task.delay(data)
            task_ids.append(result.id)

        return BigWorkflowBatchResponse(
            message="Batch queued",
            tasks=task_ids
        )
        
    except Exception as e:
        logger.error(f"Error en batch workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))