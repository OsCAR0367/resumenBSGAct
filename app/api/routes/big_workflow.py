from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import get_db
from app.schemas.workflow_schema import BigWorkflowRequest, BigWorkflowResponse
from app.services.big_workflow_service import BigWorkflowService
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
# Importante: Importar el tipo correcto para el type hint
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync

router = APIRouter(tags=["Workflow"])

@router.post("/big-workflow/test-summary", response_model=BigWorkflowResponse)
async def run_workflow_up_to_summary(
    request: BigWorkflowRequest,
    db: SQLServerClientAsync = Depends(get_db)
):
    try:
        # 1. Instanciar Repositorio (Ya actualizado para recibir SQLServerClientAsync)
        repo = ProcesamientoRepository(db)
        
        # Convertimos el modelo Pydantic a diccionario
        # Nota: En Pydantic v2 se prefiere request.model_dump(), pero .dict() funciona por compatibilidad
        data = request.dict()
        
        # 2. Crear la Sesión en BD
        # create_sesion_online es async, así que lleva await
        sesion_id = await repo.create_sesion_online(data)
        
        # 3. Instanciar e invocar Orquestador
        # BigWorkflowService __init__ debe esperar SQLServerClientAsync
        service = BigWorkflowService(db)
        
        # El orquestador ejecuta los pasos y devuelve un diccionario
        result = await service.orchestrate_up_to_summary(sesion_id, data)
        
        # Convertimos el diccionario al modelo de respuesta
        return BigWorkflowResponse(**result)

    except Exception as e:
        # Esto te mostrará el error real en la respuesta HTTP 500
        raise HTTPException(status_code=500, detail=f"Error en workflow: {str(e)}")

