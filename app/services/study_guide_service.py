import logging
import os
from pathlib import Path
from datetime import datetime

# Componentes estandarizados
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
from app.infrastructure.pdf.pdf_generator import StudyGuideGenerator
from app.infrastructure.storage.blob_storage import upload_file_to_blob_async
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

class StudyGuideService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        self.repo = ProcesamientoRepository(db)
        self.generator = StudyGuideGenerator()

    async def generate_and_upload_pdf(self, sesion_id: int, summary_text: str, pe_sesion_val: int = 0) -> str:
        """
        1. Genera PDF localmente.
        2. Sube a Azure Blob.
        3. Registra URL en BD (tabla TipoGenerar).
        """
        try:
            logger.info(f"Servicio PDF: Iniciando para sesión {sesion_id}")

            # 1. Definir rutas
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pe_sesion_val}_{timestamp}_study_guide.pdf"
            output_dir = "data/output/study_guides"
            output_path = os.path.join(output_dir, filename)

            # 2. Generar PDF (Llama a nuestra infra)
            logger.info("Generando contenido y archivo PDF...")
            await self.generator.create_study_guide(summary_text, output_path)

            # 3. Subir a Azure (Usamos la función genérica con content_type correcto)
            logger.info("Subiendo PDF a Azure Storage...")
            blob_url = await upload_file_to_blob_async(
                local_path=output_path,
                blob_subfolder=settings.AZURE_BLOB_SUBFOLDER_PDFS or "PDFs", # Asegúrate que esto esté en settings o usa string
                content_type="application/pdf"
            )

            # 4. Actualizar BD
            # Primero necesitamos saber el ID de la fila en T_ProcesamientoTipoGenerar
            # Si el workflow ya lo insertó, deberíamos tener ese ID. 
            # Si no, lo buscamos o insertamos. 
            # *Asumiremos que el frontend o el paso anterior solicitó el tipo 1 (PDF)*
            
            # Buscar el ID del registro pendiente para PDF (Tipo 1)
            # Esto es un pequeño helper query rápido:
            sql_find = """
                SELECT TOP 1 Id FROM ia.T_ProcesamientoTipoGenerar 
                WHERE IdProcesamientoSesionOnline = ? AND IdResumenGrabacionOnline = 1
            """
            row = await self.db.fetch_one(sql_find, [sesion_id])
            
            if row:
                tipo_generar_id = row['Id']
                await self.repo.update_tipo_generar(tipo_generar_id, blob_url, True)
                logger.info(f"URL de PDF actualizada en BD: {blob_url}")
            else:
                logger.warning(f"No se encontró registro TipoGenerar (PDF) para sesión {sesion_id}. Creando uno nuevo...")
                # Insertar y actualizar
                new_id = await self.repo.insert_tipo_generar(sesion_id, 1) # 1 = PDF
                await self.repo.update_tipo_generar(new_id, blob_url, True)

            # Limpieza opcional
            if os.path.exists(output_path):
                os.remove(output_path)

            return blob_url

        except Exception as e:
            logger.error(f"Fallo en StudyGuideService: {e}")
            raise e