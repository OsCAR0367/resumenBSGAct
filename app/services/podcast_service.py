import logging
import os
from pathlib import Path
from datetime import datetime

# Componentes estandarizados
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
from app.infrastructure.audio.podcast_generator import PodcastGenerator
from app.infrastructure.storage.blob_storage import upload_file_to_blob_async
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

class PodcastService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        self.repo = ProcesamientoRepository(db)
        self.generator = PodcastGenerator()

    # --- ETAPA 6: GENERAR GUION ---
    async def create_podcast_script(self, sesion_id: int, summary_text: str) -> str:
        """
        Genera el guion y lo guarda en la base de datos (campo TextoGuionAudio).
        """
        try:
            # 1. Generar texto del guion
            script = await self.generator.generate_script(summary_text)
            
            return script
        except Exception as e:
            logger.error(f"Fallo generando guion para sesión {sesion_id}: {e}")
            raise e

    # --- ETAPA 7: GENERAR AUDIO ---
    async def create_podcast_audio(self, sesion_id: int, script_text: str, pe_sesion_val: int = 0) -> str:
        """
        Genera el audio MP3, lo sube a Blob Storage y registra el entregable.
        """
        try:
            # 1. Definir rutas
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pe_sesion_val}_{timestamp}_podcast.mp3"
            output_dir = "data/output/podcast"
            output_path = os.path.join(output_dir, filename)

            # 2. Generar archivo de audio (TTS)
            logger.info("Sintetizando audio...")
            await self.generator.generate_audio_file(script_text, output_path)

            # 3. Subir a Azure Blob
            logger.info("Subiendo audio a Azure...")
            blob_url = await upload_file_to_blob_async(
                local_path=output_path,
                blob_subfolder=settings.AZURE_BLOB_SUBFOLDER_AUDIO or "ResumenAudio",
                content_type="audio/mpeg"
            )

            # 4. Registrar Entregable en BD (Tipo 3 = Podcast, según tu lógica anterior)
            # Primero buscamos si ya existe el registro pendiente
            sql_find = """
                SELECT TOP 1 Id FROM ia.T_ProcesamientoTipoGenerar 
                WHERE IdProcesamientoSesionOnline = ? AND IdResumenGrabacionOnline = 3
            """
            row = await self.db.fetch_one(sql_find, [sesion_id])
            
            if row:
                tipo_id = row['Id']
                await self.repo.update_tipo_generar(tipo_id, blob_url, True)
            else:
                # Si no existe, lo creamos
                new_id = await self.repo.insert_tipo_generar(sesion_id, 3) # 3 = Podcast
                await self.repo.update_tipo_generar(new_id, blob_url, True)

            # Limpieza
            if os.path.exists(output_path):
                os.remove(output_path)

            return blob_url

        except Exception as e:
            logger.error(f"Fallo generando audio para sesión {sesion_id}: {e}")
            raise e