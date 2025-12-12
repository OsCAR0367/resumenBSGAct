import logging
import asyncio
import os
from typing import Callable, Any
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync

from app.services.video_service import VideoService
from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.services.summarization_service import SummarizationService
from app.services.study_guide_service import StudyGuideService
from app.services.podcast_service import PodcastService

from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

class BigWorkflowService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        self.repo = ProcesamientoRepository(db)
        
        # Instanciar servicios
        self.video_service = VideoService()
        self.audio_service = AudioService(db)
        self.transcription_service = TranscriptionService(db)
        self.summarization_service = SummarizationService(db)
        self.study_guide_service = StudyGuideService(db)
        self.podcast_service = PodcastService(db)

    async def _run_step_with_retry(self, sesion_id, stage_id, func, success_msg_log):
        """
        Ejecuta la etapa y guarda el RESULTADO (texto/url) en la BD dinámicamente.
        """
        # 1. Crear registro inicial en BD
        detalle_id = await self.repo.create_detalle_etapa(sesion_id, stage_id)
        
        try:
            logger.info(f"Iniciando etapa {stage_id}...")

            await self.repo.update_detalle_estado(
                detalle_id, 
                2,  
                "Procesando...", 
                0 
            )
            
            # 2. Ejecutar la lógica de negocio (devuelve texto, url, etc.)
            result_data = await func()
            
            # 3. Guardar el RESULTADO REAL en la BD
            # Si es None, guardamos un mensaje por defecto
            content_to_save = str(result_data) if result_data else "Completado."
            
            # Actualizamos estado a 3 (Completado)
            await self.repo.update_detalle_estado(
                detalle_id, 
                3, 
                content_to_save, 
                0 
            )
            logger.info(success_msg_log)
            return result_data

        except Exception as e:
            logger.error(f"Fallo en etapa {stage_id}: {e}")
            # Actualizamos estado a 4 (Error)
            await self.repo.update_detalle_estado(
                detalle_id,
                4, 
                f"Error: {str(e)}", 
                1
            )
            raise e
        
    async def orchestrate_up_to_summary(self, sesion_id: int, data: dict) -> dict:
        """
        Orquesta el flujo completo: Video -> Audio -> Transcripción -> Resumen
        Y opcionalmente -> PDF y/o Podcast según 'TipoResumenGrabacionOnline'.
        """
        logger.info(f"--- INICIO WORKFLOW (Nativo Async) | Sesión ID: {sesion_id} ---")
        video_path = None
        
        try:
            # =================================================================
            # PASO 1: Descarga de Video
            # =================================================================
            async def _download_task():
                video_file_path = await self.video_service.download_video(
                    vimeo_url=data["UrlVideo"],
                    download_directory=str(settings.INPUT_VIDEO_DIR),
                    filename_prefix=str(sesion_id)
                )

                return video_file_path

            video_path = await self._run_step_with_retry(
                sesion_id, 
                1, 
                _download_task, 
                "Video descargado correctamente"
            )
            
            # =================================================================
            # PASO 2: Extracción de Audio
            # =================================================================
            async def _audio_task():
                resp = await self.audio_service.extract_audio(
                    video_path=video_path,
                    output_directory=str(settings.TEMP_AUDIOS_DIR)
                )
                return resp.audio_path

            audio_path = await self._run_step_with_retry(
                sesion_id,
                2, 
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
                3, 
                _transcribe_task,
                "Transcripción completada"
            )

            # =================================================================
            # PASO 4: Resumen
            # =================================================================
            async def _summary_task():
                # generate_summary_only retorna el texto sin guardar en BD (lo hace el orquestador)
                return await self.summarization_service.generate_summary_only(transcript_text)

            summary_text = await self._run_step_with_retry(
                sesion_id, 
                4, 
                _summary_task, 
                "Resumen generado y guardado."
            )

            # =================================================================
            # PASOS OPCIONALES (PDF / PODCAST)
            # =================================================================
            
            # Obtenemos la lista de tipos solicitados [1, 3, etc]
            tipos_solicitados = data.get("TipoResumenGrabacionOnline", [])
            
            # Inicializamos variables para capturar las URLs
            pdf_url_result = None
            podcast_url_result = None

            # --- ETAPA 5: GENERACIÓN DE PDF (Si ID 1 está en la lista) ---
            if 1 in tipos_solicitados:
                async def _pdf_task():
                    # Usamos un valor identificador opcional o 0 para el nombre del archivo
                    pe_sesion_val = data.get("IdPEspecificoSesion", 0)
                    
                    # Llamamos al servicio que genera, sube a Azure y devuelve la URL
                    return await self.study_guide_service.generate_and_upload_pdf(
                        sesion_id=sesion_id,
                        summary_text=summary_text,
                        pe_sesion_val=pe_sesion_val
                    )

                # Ejecutamos la tarea y CAPTURAMOS la URL
                pdf_url_result = await self._run_step_with_retry(
                    sesion_id,
                    5, # ID Etapa: GeneracionPDF
                    _pdf_task,
                    "PDF generado y subido a Azure"
                )
            else:
                logger.info("Paso PDF (Tipo 1) no solicitado.")

            # --- ETAPAS 6 y 7: PODCAST (Si ID 3 está en la lista) ---
            if 3 in tipos_solicitados:
                # Sub-Paso 6: Guion (Intermedio)
                async def _script_task():
                    return await self.podcast_service.create_podcast_script(
                        sesion_id=sesion_id, 
                        summary_text=summary_text
                    )

                script_text = await self._run_step_with_retry(
                    sesion_id,
                    6, # ID Etapa: GeneracionGuionPodcast
                    _script_task,
                    "Guion de podcast generado"
                )

                # Sub-Paso 7: Audio Podcast (Final)
                async def _podcast_audio_task():
                    pe_sesion_val = data.get("IdPEspecificoSesion", 0)
                    # Este servicio genera audio, sube a Azure y retorna la URL
                    return await self.podcast_service.create_podcast_audio(
                        sesion_id=sesion_id,
                        script_text=script_text,
                        pe_sesion_val=pe_sesion_val
                    )

                # Ejecutamos la tarea y CAPTURAMOS la URL
                podcast_url_result = await self._run_step_with_retry(
                    sesion_id,
                    7, # ID Etapa: GeneracionAudioPodcast
                    _podcast_audio_task,
                    "Audio Podcast generado y subido a Azure"
                )
            else:
                logger.info("Paso Podcast (Tipo 3) no solicitado.")

            # --- RETORNO FINAL CON URLs ---
            return {
                "message": "Workflow completado exitosamente",
                "sesion_id": sesion_id,
                "status": "success",
                "summary_preview": summary_text[:100] + "...",
                # Devolvemos las URLs generadas (serán None si no se solicitaron)
                "pdf_url": pdf_url_result,
                "podcast_url": podcast_url_result
            }

        except Exception as e:
            # El error ya se registró en la BD dentro de _run_step_with_retry
            # Aquí solo relanzamos para que el endpoint responda 500
            raise e
            
        finally:
            # Limpieza del video original
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info("Video temporal eliminado.")
                except:
                    pass