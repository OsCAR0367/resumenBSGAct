from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Importamos el servicio de procesamiento masivo
from app.services.batch_manager_service import BatchManagerService

router = APIRouter(tags=["Batch Processing"])

# --- Esquema de Entrada (Input Schema) ---
class BigWorkflowRequest(BaseModel):
    IdPEspecifico: int
    IdPEspecificoSesion: int
    Sesion: str
    UrlVideo: str
    Usuario: str
    TipoResumenGrabacionOnline: Optional[List[int]] = []

# --- Esquema de Respuesta (Para ver los resultados en Swagger) ---
class BatchResultResponse(BaseModel):
    total_processed: int
    success: int
    failed: int
    results: List[Any] # Aquí vendrá el detalle de cada video (URLs, IDs, etc.)

@router.post("/batch/start-process-sync", response_model=BatchResultResponse)
async def start_batch_processing_sync(
    requests: List[BigWorkflowRequest]
):
    """
    Recibe una lista de videos, los procesa y ESPERA a que terminen.
    Devuelve el reporte completo con URLs y estados al finalizar.
    
    NOTA: Si envías muchos videos, esto puede tardar mucho y dar Timeout en el cliente.
    """
    if not requests:
        raise HTTPException(status_code=400, detail="La lista de videos está vacía.")

    # Instanciamos el servicio (él crea su propia conexión a DB)
    service = BatchManagerService()
    
    # Convertimos los modelos Pydantic a una lista de diccionarios
    data_list = [req.dict() for req in requests]

    final_report = await service.process_batch_list(data_list, batch_size=10)

    return final_report