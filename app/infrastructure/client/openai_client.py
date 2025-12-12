import logging
from typing import Dict, Any, List, Optional, Union, BinaryIO
from app.infrastructure.api_client import api_client_async

logger = logging.getLogger(__name__)

class OpenAIClient:
    """
    Cliente asíncrono robusto y genérico para la API REST de OpenAI.    
    Cubre:
    - Chat Completions (GPT-4, etc.)
    - Embeddings (Text-Embedding-3)
    - Audio (Whisper Transcription / TTS)
    - Image Generation (DALL-E)
    - Modelos
    """

    def __init__(
        self, 
        api_key: str, 
        organization_id: Optional[str] = None,
        project_id: Optional[str] = None,
        timeout: int = 60,
        base_url: str = "https://api.openai.com/v1"
    ):
        """
        Inicializa el cliente de OpenAI.

        :param api_key: La llave de API (sk-...).
        :param organization_id: (Opcional) ID de la organización para facturación.
        :param project_id: (Opcional) ID del proyecto para control de acceso.
        :param timeout: Tiempo máximo de espera en segundos (Default: 60s).
        :param base_url: URL base (para uso proxy o Azure OpenAI).
        """
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Headers organizacionales 
        if organization_id:
            self.headers["OpenAI-Organization"] = organization_id
        if project_id:
            self.headers["OpenAI-Project"] = project_id

        # Instancia del cliente HTTP genérico
        self.http_client = api_client_async.ApiClientAsync(
            base_url=self.base_url,
            default_headers=self.headers,
            timeout=timeout
        )

    # ==========================================================================
    # 1. CHAT COMPLETIONS (GPT-4o,etc.)
    # ==========================================================================
    
    async def create_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Genera una respuesta de chat. Devuelve el JSON completo de OpenAI.
        
        :param messages: Historial de chat [{"role": "user", "content": "hola"}].
        :param model: ID del modelo a usar.
        :param temperature: Creatividad (0.0 a 2.0).
        :param response_format: Ej: {"type": "json_object"} para forzar JSON.
        :param kwargs: Parámetros extra (top_p, frequency_penalty, tools, etc.).
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs # Permite pasar cualquier parámetro nuevo que saque OpenAI
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format

        logger.info(f"OpenAI: Chat Completion request ({model})")
        
        async with self.http_client as client:
            try:
                return await client.post_async(endpoint="chat/completions", json_data=payload)
            except Exception as e:
                logger.error(f"OpenAI Chat Error: {e}")
                raise e

    # ==========================================================================
    # 2. EMBEDDINGS (Para RAG y Búsqueda Semántica)
    # ==========================================================================

    async def create_embeddings(
        self, 
        input_text: Union[str, List[str]], 
        model: str = "text-embedding-3-small",
        dimensions: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera vectores (embeddings) para un texto o lista de textos.
        
        :param input_text: Texto o lista de textos a vectorizar.
        :param model: Modelo de embedding.
        :param dimensions: (Opcional) Reducir dimensiones del vector (solo modelos v3).
        """
        payload = {
            "input": input_text,
            "model": model
        }
        if dimensions:
            payload["dimensions"] = dimensions

        logger.info(f"OpenAI: Embedding request ({model})")

        async with self.http_client as client:
            try:
                return await client.post_async(endpoint="embeddings", json_data=payload)
            except Exception as e:
                logger.error(f"OpenAI Embedding Error: {e}")
                raise e

    # ==========================================================================
    # 3. AUDIO (Whisper - Transcripción)
    # ==========================================================================

    async def create_transcription(
        self, 
        file_bytes: bytes, 
        filename: str,
        model: str = "whisper-1",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Transcribe audio a texto usando Whisper.
        NOTA: Este endpoint usa multipart/form-data, no JSON.
        
        :param file_bytes: Bytes del archivo de audio.
        :param filename: Nombre del archivo (necesario para que OpenAI detecte el formato, ej: 'audio.mp3').
        """
        # Preparar form-data
        files = {
            "file": (filename, file_bytes)
        }
        data = {
            "model": model,
            "response_format": response_format
        }
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt

        logger.info(f"OpenAI: Transcription request ({filename})")

        # IMPORTANTE: Para subir archivos, httpx usar el parámetro 'files'.
        # Pasamos 'files' y 'data' (para los campos de texto) a través de **kwargs de tu cliente genérico.
        
        headers_copy = self.headers.copy()
        headers_copy.pop("Content-Type", None)

        async with self.http_client as client:
            try:
                return await client.post_async(
                    endpoint="audio/transcriptions", 
                    headers=headers_copy,
                    files=files, # httpx kwarg
                    data=data    # httpx kwarg para campos de formulario
                )
            except Exception as e:
                logger.error(f"OpenAI Transcription Error: {e}")
                raise e

    # ==========================================================================
    # 4. AUDIO (TTS - Text to Speech)
    # ==========================================================================

    async def create_speech(
        self,
        input_text: str,
        voice: str = "alloy",
        model: str = "tts-1",
        response_format: str = "mp3"
    ) -> bytes:
        """
        Genera audio a partir de texto.
        Devuelve los bytes del audio (binario).
        """
        payload = {
            "model": model,
            "input": input_text,
            "voice": voice,
            "response_format": response_format
        }

        logger.info(f"OpenAI: TTS request ({voice})")

        async with self.http_client as client:
            try:
                # Usamos request_async directamente porque necesitamos el contenido binario (content), no .json()
                
                stream_ctx = await client.post_async(
                    endpoint="audio/speech", 
                    json_data=payload,
                    stream=True # Pedimos stream para evitar el .json() automático
                )
                
                async with stream_ctx as response:
                    response.raise_for_status()
                    return await response.read() # Leemos todo el binario en memoria

            except Exception as e:
                logger.error(f"OpenAI TTS Error: {e}")
                raise e

    # ==========================================================================
    # 5. IMÁGENES (DALL-E 3)
    # ==========================================================================

    async def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> Dict[str, Any]:
        """
        Genera imágenes a partir de texto.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality
        }

        logger.info(f"OpenAI: Image Generation request ({size})")

        async with self.http_client as client:
            try:
                return await client.post_async(endpoint="images/generations", json_data=payload)
            except Exception as e:
                logger.error(f"OpenAI Image Error: {e}")
                raise e

    # ==========================================================================
    # HELPER METHODS (Utilidades para simplificar el uso)
    # ==========================================================================

    def extract_text_content(self, response: Dict[str, Any]) -> str:
        """
        Extrae solo el texto de una respuesta estándar de Chat Completion.
        Útil para no tener que hacer response['choices'][0]... cada vez.
        """
        try:
            return response["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            return ""