import logging
import asyncio
import os
from typing import Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession  # <--- Importante: AsyncSession

# Servicios de Dominio
from app.services.video_service import VideoService
from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.services.summarization_service import SummarizationService

# Repositorio y Config
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
from app.daemons.config import Config

logger = logging.getLogger(__name__)

class BigWorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProcesamientoRepository(db)
        
        # Instanciar servicios
        self.video_service = VideoService()
        self.audio_service = AudioService(db)
        self.transcription_service = TranscriptionService(db)
        self.summarization_service = SummarizationService(db)

    async def _run_step_with_retry(
        self, 
        sesion_id: int, 
        stage_id: int, 
        func: Callable, 
        success_message: str
    ) -> Any:
        """
        Ejecuta una etapa con lógica de reintentos de forma nativa ASÍNCRONA.
        """
        # 1. Crear registro inicial (Estado 2: En Proceso) - AWAIT DIRECTO
        detalle_id = await self.repo.create_detalle_etapa(sesion_id, stage_id)
        
        errores_count = 0
        max_retries = 3

        while errores_count < max_retries:
            try:
                # Intentar ejecutar la función de servicio
                logger.info(f"Ejecutando etapa {stage_id} (Intento {errores_count + 1}/{max_retries})...")
                result = await func()
                
                # ÉXITO: Actualizar a Estado 3 (Completado) 
                await self.repo.update_detalle_estado(
                    detalle_id, 
                    3, # Completado
                    success_message, 
                    errores_count 
                )
                return result

            except Exception as e:
                errores_count += 1
                logger.warning(f"Fallo en etapa {stage_id} (Intento {errores_count}): {str(e)}")

                if errores_count < max_retries:
                    # REINTENTO: Mantenemos Estado 2 (En Proceso) 
                    await self.repo.update_detalle_estado(
                        detalle_id,
                        2, # En Proceso
                        f"Reintentando ejecución... ({errores_count}/{max_retries})",
                        errores_count
                    )
                    # Espera no bloqueante
                    await asyncio.sleep(errores_count)
                else:
                    # FALLO FINAL: Estado 4 (Error) 
                    logger.error(f"Etapa {stage_id} falló definitivamente tras {max_retries} intentos.")
                    
                    await self.repo.update_detalle_estado(
                        detalle_id,
                        4, # Error
                        f"Fallo crítico: {str(e)}", 
                        errores_count
                    )
                    raise e

    async def orchestrate_up_to_summary(self, sesion_id: int, data: dict) -> dict:
        """
        Orquesta el flujo paso a paso usando los servicios asíncronos.
        """
        logger.info(f"--- INICIO WORKFLOW (Nativo Async) | Sesión ID: {sesion_id} ---")
        video_path = None
        
        try:
            # =================================================================
            # PASO 1: Descarga de Video
            # =================================================================
            async def _download_task():
                resp = await self.video_service.download_video(
                    vimeo_url=data["UrlVideo"],
                    download_directory=str(Config.INPUT_VIDEO_DIR) or "data/input/videos"
                )
                return resp.file_path

            video_path = await self._run_step_with_retry(
                sesion_id, 
                1, # Descarga
                _download_task, 
                "Video descargado correctamente"
            )
            
            # =================================================================
            # PASO 2: Extracción de Audio
            # =================================================================
            async def _audio_task():
                resp = await self.audio_service.extract_audio(
                    video_path=video_path,
                    output_directory=str(Config.TEMP_AUDIOS_DIR) or "data/temp/audios"
                )
                return resp.audio_path

            audio_path = await self._run_step_with_retry(
                sesion_id,
                2, # Audio
                _audio_task,
                "Audio extraído correctamente"
            )

            # =================================================================
            # PASO 3: Transcripción
            # =================================================================
            async def _transcribe_task():
                text = await self.transcription_service.transcribe_audio_file(
                    audio_path=audio_path,
                    session_id=sesion_id
                )
                if not text or len(text) < 10:
                    raise ValueError("Texto vacío.")
                return text

            transcript_text = await self._run_step_with_retry(
                sesion_id,
                3, # Transcripción
                _transcribe_task,
                "Transcripción completada"
            )

            # =================================================================
            # PASO 4: Resumen
            # =================================================================
            async def _summary_task():
                return await self.summarization_service.generate_and_save_summary(
                    session_id=sesion_id,
                    transcription_text=transcript_text
                )

            summary_text = await self._run_step_with_retry(
                sesion_id,
                4, # Resumen
                _summary_task,
                "Resumen generado exitosamente"
            )

            return {
                "message": "Workflow completado",
                "sesion_id": sesion_id,
                "status": "success",
                "summary_preview": summary_text[:100] + "..."
            }

        except Exception as e:
            # El error ya fue registrado en BD por _run_step_with_retry
            raise e
            
        finally:
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info("Video temporal eliminado.")
                except:
                    pass