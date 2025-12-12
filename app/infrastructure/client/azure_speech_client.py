import logging
from typing import Dict, Any, List, Optional, Union
from app.infrastructure.api_client import api_client_async

logger = logging.getLogger(__name__)

class AzureSpeechClient:
    """
    Cliente asíncrono robusto para Azure Cognitive Services - Speech to Text (Batch API v3.2).
    
    Documentación oficial: 
    https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-transcription
    """

    def __init__(self, subscription_key: str, region: str, timeout: int = 100):
        """
        :param subscription_key: Clave de Ocp-Apim-Subscription-Key.
        :param region: Región del recurso (ej: 'eastus', 'westeurope').
        :param timeout: Timeout para las peticiones HTTP (default 100s).
        """
        # La URL base depende de la región
        self.base_url = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.2"
        
        self.headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "Content-Type": "application/json"
        }
        
        # Instancia del cliente HTTP genérico
        self.http_client = api_client_async.ApiClientAsync(
            base_url=self.base_url,
            default_headers=self.headers,
            timeout=timeout
        )

    # ==========================================================================
    # 1. CREAR TRANSCRIPCIÓN (POST)
    # ==========================================================================

    async def start_transcription(
        self, 
        audio_urls: List[str], 
        job_name: str,
        locale: str = "es-ES",
        diarization_enabled: bool = False,
        word_level_timestamps: bool = False,
        profanity_filter_mode: str = "Masked",
        punctuation_mode: str = "DictatedAndAutomatic",
        model_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Inicia un trabajo de transcripción por lotes.
        
        :param audio_urls: Lista de URLs (SAS Tokens o Públicas) de los audios.
        :param job_name: Nombre identificativo para el trabajo.
        :param locale: Idioma del audio (ej: 'es-PE', 'en-US').
        :param diarization_enabled: Si True, separa hablantes (Speaker 1, Speaker 2).
        :param model_id: (Opcional) ID de un modelo personalizado entrenado (Custom Speech).
        :param kwargs: Propiedades adicionales soportadas por Azure.
        :return: JSON de respuesta de Azure (contiene el ID y enlaces 'self').
        """
        
        # Construcción de propiedades (Configuration)
        properties = {
            "diarizationEnabled": diarization_enabled,
            "wordLevelTimestampsEnabled": word_level_timestamps,
            "profanityFilterMode": profanity_filter_mode,
            "punctuationMode": punctuation_mode,
            **kwargs
        }

        payload = {
            "contentUrls": audio_urls,
            "displayName": job_name,
            "locale": locale,
            "properties": properties
        }

        # Si se usa un modelo personalizado (Custom Speech)
        if model_id:
            payload["model"] = {"self": f"{self.base_url}/models/{model_id}"}

        logger.info(f"AzureSpeech: Iniciando transcripción '{job_name}' (Locale: {locale})")

        async with self.http_client as client:
            try:
                # POST /transcriptions
                response = await client.post_async(endpoint="transcriptions", json_data=payload)
                return response
            except Exception as e:
                logger.error(f"AzureSpeech Error al iniciar job: {e}")
                raise e

    # ==========================================================================
    # 2. CONSULTAR ESTADO (POLLING)
    # ==========================================================================

    async def get_transcription_job(self, transcription_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual de un trabajo específico.
        Útil para el bucle de polling (Running -> Succeeded).
        
        :param transcription_id: El ID que Azure retornó al crear (no la URL completa).
        """
        async with self.http_client as client:
            try:
                # GET /transcriptions/{id}
                return await client.get_async(endpoint=f"transcriptions/{transcription_id}")
            except Exception as e:
                logger.error(f"AzureSpeech Error consultando estado ({transcription_id}): {e}")
                raise e

    # ==========================================================================
    # 3. OBTENER RESULTADOS (ARCHIVOS)
    # ==========================================================================

    async def get_transcription_files(self, transcription_id: str) -> Dict[str, Any]:
        """
        Obtiene la lista de archivos generados (transcripción JSON, reporte, etc.).
        
        :param transcription_id: ID del trabajo exitoso.
        :return: JSON con la lista de 'values' (cada uno es un archivo con su link de descarga).
        """
        logger.info(f"AzureSpeech: Obteniendo archivos para {transcription_id}")
        async with self.http_client as client:
            try:
                # GET /transcriptions/{id}/files
                return await client.get_async(endpoint=f"transcriptions/{transcription_id}/files")
            except Exception as e:
                logger.error(f"AzureSpeech Error listando archivos: {e}")
                raise e

    # ==========================================================================
    # 4. GESTIÓN (LISTAR / BORRAR)
    # ==========================================================================

    async def delete_transcription(self, transcription_id: str) -> None:
        """
        Elimina el registro de la transcripción en Azure.
        IMPORTANTE: Azure tiene límites de almacenamiento de historial. 
        Es buena práctica borrar el job después de descargar el JSON.
        """
        logger.info(f"AzureSpeech: Eliminando registro {transcription_id}")
        async with self.http_client as client:
            try:
                await client.delete_async(endpoint=f"transcriptions/{transcription_id}")
            except Exception as e:
                logger.warning(f"AzureSpeech Warning: No se pudo borrar {transcription_id}: {e}")
                # No lanzamos error crítico, borrar es opcional

    # ==========================================================================
    # HELPER METHODS (Utilidades)
    # ==========================================================================

    async def download_transcript_content(self, file_url: str) -> Dict[str, Any]:
        """
        Descarga el JSON real de la transcripción desde la URL de Azure Storage que devuelve la API.
        
        NOTA: La URL de descarga es absoluta (ej: https://blob.core...).
        Usamos un cliente temporal sin base_url para esto.
        """
        # Cliente "vacío" para URLs absolutas
        temp_client = api_client_async.ApiClientAsync(base_url="", default_headers={}) 
        
        async with temp_client as client:
            try:
                # Al pasar la URL completa en endpoint y base_url vacía, funciona.
                return await client.get_async(endpoint=file_url)
            except Exception as e:
                logger.error(f"AzureSpeech Error descargando contenido JSON: {e}")
                raise e