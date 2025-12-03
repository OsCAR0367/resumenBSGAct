import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session

# Importamos nuestras nuevas infraestructuras asíncronas
from app.infrastructure.storage.blob_storage import upload_audio_to_blob_async
from app.infrastructure.transcription.azure_client import AzureSpeechClient

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.speech_client = AzureSpeechClient()

    async def transcribe_audio_file(self, audio_path: str, session_id: int = 0) -> str:
        """
        Flujo completo de transcripción asíncrona:
        1. Subir audio a Blob (Async Thread) -> SAS URL
        2. Enviar Job a Azure (Async IO)
        3. Polling (Async IO)
        4. Descargar texto (Async IO)
        
        Retorna:
            str: El texto transcrito.
        """
        try:
            # 1. Subir a Blob Storage
            logger.info(f"Servicio: Subiendo audio para sesión {session_id}...")
            sas_url = await upload_audio_to_blob_async(
                local_path=audio_path, 
                blob_subfolder="AudioSesion"
            )
            
            # 2. Enviar trabajo de transcripción
            job_name = f"sesion_{session_id}_{datetime.now().strftime('%Y%m%d%H%M')}"
            logger.info(f"Servicio: Enviando trabajo a Azure Speech: {job_name}")
            
            polling_url = await self.speech_client.submit_job(sas_url, job_name)
            
            # 3. Esperar resultado (Polling inteligente)
            logger.info("Servicio: Esperando finalización (Polling)...")
            job_result = await self.speech_client.poll_until_complete(polling_url, interval=5)
            
            # 4. Obtener texto
            transcript_text = await self.speech_client.fetch_transcript_text(job_result)
            
            logger.info("Servicio: Transcripción obtenida exitosamente.")
            
            # (Opcional) Guardar en disco local si se requiere respaldo
            self._save_local_backup(transcript_text, session_id)
            
            # (Opcional) Actualizar BD usando self.db
            # self.repo.update_transcription(session_id, transcript_text)
            
            return transcript_text

        except Exception as e:
            logger.error(f"Error en TranscriptionService: {str(e)}")
            raise e

    def _save_local_backup(self, text: str, session_id: int):
        """Helper simple para guardar un backup del texto."""
        try:
            output_dir = "data/output/transcriptions"
            os.makedirs(output_dir, exist_ok=True)
            path = os.path.join(output_dir, f"transcription_{session_id}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.warning(f"No se pudo guardar backup local: {e}")