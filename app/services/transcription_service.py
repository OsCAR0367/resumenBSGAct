import logging
import asyncio
import os
from datetime import datetime
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.core.setup_config import settings

from app.infrastructure.storage.blob_storage import upload_file_to_blob_async

from app.infrastructure.client.azure_speech_client import AzureSpeechClient

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        self.azure_client = AzureSpeechClient(
            subscription_key=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )

    async def transcribe_audio_file(self, audio_path: str, session_id: int = 0) -> str:
        """
        Orquesta el flujo completo:
        1. Subida a Blob Storage (obtiene SAS URL).
        2. Envío a Azure Speech (Batch API).
        3. Polling de estado (Cada 100s).
        4. Descarga y limpieza.
        """
        try:
            # -----------------------------------------------------------
            # PASO 1: Subir a Blob Storage
            # -----------------------------------------------------------
            logger.info(f"Servicio: Subiendo audio para sesión {session_id}...")
            
            sas_url = await upload_file_to_blob_async(
                local_path=audio_path, 
                blob_subfolder=settings.AZURE_BLOB_SUBFOLDER_AUDIOSESION 
            )
            
            # -----------------------------------------------------------
            # PASO 2: Iniciar Transcripción
            # -----------------------------------------------------------
            job_name = f"sesion_{session_id}_{datetime.now().strftime('%Y%m%d%H%M')}"
            
            job_response = await self.azure_client.start_transcription(
                audio_urls=[sas_url],
                job_name=job_name,
                locale="es-PE", 
                diarization_enabled=True
            )
            
            # Extraer ID del trabajo
            job_self_url = job_response["self"]
            transcription_id = job_self_url.split("/")[-1]
            
            logger.info(f"Servicio: Job creado ID: {transcription_id}. Iniciando espera (Polling)...")

            # -----------------------------------------------------------
            # PASO 3: Polling (Esperar a que termine)
            # -----------------------------------------------------------
            while True:
                # Consultamos estado
                status_data = await self.azure_client.get_transcription_job(transcription_id)
                status = status_data["status"]
                
                if status == "Succeeded":
                    logger.info(f"Azure: Transcripción finalizada correctamente ({status}).")
                    break
                elif status == "Failed":
                    error_msg = status_data.get("properties", {}).get("error", {}).get("message", "Error desconocido")
                    raise Exception(f"Azure Speech falló: {error_msg}")
                
                logger.info(f"Azure: Estado '{status}'. Esperando 100 segundos...")
                await asyncio.sleep(100) 

            # -----------------------------------------------------------
            # PASO 4: Obtener Resultados y Texto
            # -----------------------------------------------------------
            files_response = await self.azure_client.get_transcription_files(transcription_id)
            
            transcript_json_url = None
            for f in files_response["values"]:
                if f["kind"] == "Transcription":
                    transcript_json_url = f["links"]["contentUrl"]
                    break
            
            if not transcript_json_url:
                raise Exception("Azure terminó pero no generó archivo de transcripción.")

            full_json = await self.azure_client.download_transcript_content(transcript_json_url)
            
            final_text = full_json["combinedRecognizedPhrases"][0]["display"]
            
            logger.info("Servicio: Texto descargado exitosamente.")

            # -----------------------------------------------------------
            # PASO 5: Limpieza y Backup
            # -----------------------------------------------------------
            await self.azure_client.delete_transcription(transcription_id)
            self._save_local_backup(final_text, session_id)
            
            return final_text

        except Exception as e:
            logger.error(f"Error en TranscriptionService: {str(e)}")
            raise e

    def _save_local_backup(self, text: str, session_id: int):
        """Helper simple para guardar un backup del texto."""
        try:
            output_dir = str(settings.TRANSCRIPTIONS_OUTPUT_DIR)
            os.makedirs(output_dir, exist_ok=True)
            path = os.path.join(output_dir, f"transcription_{session_id}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.warning(f"No se pudo guardar backup local: {e}")