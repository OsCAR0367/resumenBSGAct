import asyncio
import logging
from typing import List
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.services.big_workflow_service import BigWorkflowService
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository

logger = logging.getLogger(__name__)

class BatchManagerService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        self.workflow_service = BigWorkflowService(db)
        self.repo = ProcesamientoRepository(db)

    async def _process_single_item(self, data: dict) -> dict:
        """
        Procesa un único ítem de principio a fin.
        """
        try:
            # 1. Crear Sesión en BD
            sesion_id = await self.repo.create_sesion_online(data)
            
            # 2. Ejecutar Workflow
            logger.info(f"[Item] Iniciando Sesión {sesion_id} ({data.get('Sesion')})")
            result = await self.workflow_service.orchestrate_up_to_summary(sesion_id, data)
            
            return {
                "input_id": data.get("IdPEspecifico"),
                "sesion_id": sesion_id,
                "status": "success",
                "details": result
            }
        except Exception as e:
            logger.error(f"[Item] Error en '{data.get('Sesion')}' (ID: {data.get('IdPEspecifico')}): {e}")
            return {
                "input_id": data.get("IdPEspecifico"),
                "status": "error",
                "error": str(e)
            }

    async def process_batch_list(self, requests_data: List[dict], batch_size: int = 10) -> dict:
        """
        Procesa la lista dividiéndola en lotes estrictos de 'batch_size'.
        Espera a que termine un lote completo antes de iniciar el siguiente.
        """
        results = []
        total_items = len(requests_data)
        
        logger.info(f"=== INICIO PROCESAMIENTO POR LOTES: {total_items} items (Lotes de {batch_size}) ===")

        # Bucle para dividir la lista en trozos (chunks) de 10
        for i in range(0, total_items, batch_size):
            # Obtener el sub-grupo actual (ej: del 0 al 10, luego del 10 al 20...)
            current_batch_data = requests_data[i : i + batch_size]
            batch_number = (i // batch_size) + 1
            
            logger.info(f"--- PROCESANDO LOTE {batch_number} (Items {i+1} a {min(i+batch_size, total_items)}) ---")
            
            # Crear las tareas del lote actual
            tasks = [self._process_single_item(item) for item in current_batch_data]
            
            # asyncio.gather lanza las 10 a la vez y ESPERA a que TODAS terminen
            batch_results = await asyncio.gather(*tasks)
            
            # Guardamos resultados y continuamos
            results.extend(batch_results)
            logger.info(f"--- FIN LOTE {batch_number}. Iniciando siguiente bloque... ---")

        # Estadísticas finales
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"=== PROCESO FINALIZADO. Éxito: {success_count}/{total_items} ===")
        
        return {
            "total_processed": total_items,
            "success": success_count,
            "failed": total_items - success_count,
            "results": results
        }