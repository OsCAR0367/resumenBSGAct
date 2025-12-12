import asyncio
import logging
from typing import List

# Importamos TU cliente existente
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.core.setup_config import settings 

# Importamos los servicios del flujo
from app.services.big_workflow_service import BigWorkflowService
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository

logger = logging.getLogger(__name__)

class BatchManagerService:
    def __init__(self, db: SQLServerClientAsync = None):
        self.db = db

    async def _process_single_item(self, data: dict) -> dict:
        """
        Procesa un ítem creando SU PROPIA CONEXIÓN usando tu clase existente.
        """
        # 1. Instanciamos el cliente 
        dsn = settings.get_database_sql_server_url()
        client = SQLServerClientAsync(dsn)

        # 2. Usamos 'async with' para abrir y cerrar esta conexión específica
        async with client as db_connection:
            try:
                # 3. Le pasamos esta conexión única al Repo y al Workflow
                repo = ProcesamientoRepository(db_connection)
                workflow_service = BigWorkflowService(db_connection)

                # --- LÓGICA DE NEGOCIO ---
                
                # A. Crear Sesión en BD
                sesion_id = await repo.create_sesion_online(data)
                
                # B. Ejecutar Workflow (Video -> Audio -> IA -> PDF/Podcast)
                logger.info(f"[Item] Iniciando Sesión {sesion_id} ({data.get('Sesion')})")
                result = await workflow_service.orchestrate_up_to_summary(sesion_id, data)
                
                return {
                    "input_id": data.get("IdPEspecifico"),
                    "sesion_id": sesion_id,
                    "status": "success",
                    "details": result
                }
                
            except Exception as e:
                # Capturamos error para no detener a los otros 9
                logger.error(f"[Item] Error en '{data.get('Sesion')}' (ID: {data.get('IdPEspecifico')}): {e}")
                return {
                    "input_id": data.get("IdPEspecifico"),
                    "status": "error",
                    "error": str(e)
                }

    async def process_batch_list(self, requests_data: List[dict], batch_size: int = 10) -> dict:
        """
        Orquestador que divide la lista y lanza tareas paralelas.
        """
        results = []
        total_items = len(requests_data)
        
        logger.info(f"=== INICIO BATCH: {total_items} items (Paralelismo: {batch_size}) ===")

        for i in range(0, total_items, batch_size):
            # Tomar grupo de 10
            current_batch_data = requests_data[i : i + batch_size]
            batch_number = (i // batch_size) + 1
            
            logger.info(f"--- PROCESANDO LOTE {batch_number} ---")
            
            # Crear las 10 tareas. Cada una llamará a _process_single_item y abrirá su propia conexión.
            tasks = [self._process_single_item(item) for item in current_batch_data]
            
            # Ejecutar las 10 a la vez y esperar a que terminen
            batch_results = await asyncio.gather(*tasks)
            
            results.extend(batch_results)
            logger.info(f"--- LOTE {batch_number} FINALIZADO ---")

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"=== FIN TOTAL. Éxito: {success_count}/{total_items} ===")
        
        return {
            "total_processed": total_items,
            "success": success_count,
            "failed": total_items - success_count,
            "results": results
        }