from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Dependencias y Configuración
from app.api.dependencies import get_db
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync

# Servicio de Lotes
from app.services.batch_manager_service import BatchManagerService

router = APIRouter(tags=["Batch Processing"])

# --- Esquema de Entrada (Input Schema) ---
# Definimos aquí el modelo para validar los datos que entran
class BigWorkflowRequest(BaseModel):
    IdPEspecifico: int
    IdPEspecificoSesion: int
    Sesion: str
    UrlVideo: str
    Usuario: str
    # Lista opcional de enteros (ej: [1, 3] para PDF y Podcast)
    TipoResumenGrabacionOnline: Optional[List[int]] = []

@router.post("/batch/start-process")
async def start_batch_processing(
    requests: List[BigWorkflowRequest], # FastAPI espera una LISTA de objetos JSON
    background_tasks: BackgroundTasks,  # Magia de FastAPI para correr en segundo plano
    db: SQLServerClientAsync = Depends(get_db)
):
    """
    Recibe una lista de videos y los procesa en lotes de 10 en fondo.
    Responde inmediatamente "Procesamiento iniciado".
    """
    if not requests:
        raise HTTPException(status_code=400, detail="La lista de videos está vacía.")

    # Instanciamos el servicio gestor de lotes
    service = BatchManagerService(db)
    
    # Convertimos los objetos Pydantic a diccionarios simples
    # para que el servicio los entienda
    data_list = [req.dict() for req in requests]

    # Lanzamos la tarea en Background (Fire and Forget)
    # batch_size=10 para procesar de 10 en 10
    background_tasks.add_task(service.process_batch_list, data_list, batch_size=10)

    return {
        "message": f"🚀 Procesamiento masivo iniciado para {len(data_list)} videos.",
        "mode": "Background Async (Lotes Estrictos)",
        "batch_size": 10,
        "note": "El servidor procesará 10 videos, esperará a que terminen, y tomará los siguientes 10."
    }