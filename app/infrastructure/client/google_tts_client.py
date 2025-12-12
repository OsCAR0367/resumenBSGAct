import logging
import base64
import aiofiles
import google.auth.transport.requests
from google.oauth2 import service_account
from typing import Optional, Dict, Any

# Tu cliente genérico
from app.infrastructure.api_client import api_client_async

logger = logging.getLogger(__name__)

class GoogleTTSClient:
    """
    Cliente asíncrono estandarizado para Google Cloud TTS usando SERVICE ACCOUNT (JSON).
    Genera tokens OAuth 2.0 automáticamente.
    """

    def __init__(self, json_credentials_path: str, timeout: int = 30):
        """
        :param json_credentials_path: Ruta al archivo .json de la Service Account.
        :param timeout: Tiempo máximo de espera.
        """
        self.base_url = "https://texttospeech.googleapis.com/v1"
        self.timeout = timeout
        
        # 1. Cargar credenciales desde el JSON
        self.scopes = ['https://www.googleapis.com/auth/cloud-platform']
        self.creds = service_account.Credentials.from_service_account_file(
            json_credentials_path, 
            scopes=self.scopes
        )
        

    def _get_access_token(self) -> str:
        """
        Refresca y obtiene un token válido usando las credenciales de Google.
        síncrono(computacional).
        """
        # Crear una petición de transporte para refrescar el token
        auth_req = google.auth.transport.requests.Request()
        
        # Refrescar token (si ha expirado o no existe)
        self.creds.refresh(auth_req)
        
        return self.creds.token

    async def synthesize_speech(
        self,
        text: str,
        voice_name: str = "es-US-Polyglot-1",
        language_code: str = "es-US",
        audio_encoding: str = "MP3",
        speaking_rate: float = 1.0
    ) -> bytes:
        """
        Realiza la petición REST usando el Token generado.
        """
        # 1. Obtener Token fresco (Bearer)
        token = self._get_access_token()

        # 2. Configurar Headers dinámicos con el Token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        # 3. Preparar Payload
        payload = {
            "input": {"text": text},
            "voice": {"languageCode": language_code, "name": voice_name},
            "audioConfig": {
                "audioEncoding": audio_encoding,
                "speakingRate": speaking_rate
            }
        }

        logger.info(f"GoogleTTS: Sintetizando ({len(text)} chars)...")

        # 4. Usar el cliente genérico
        # Usamos context manager para abrir/cerrar conexión limpiamente
        async with api_client_async.ApiClientAsync(
            base_url=self.base_url,
            default_headers=headers,
            timeout=self.timeout
        ) as client:
            try:
                # POST /text:synthesize
                response = await client.post_async(endpoint="text:synthesize", json_data=payload)
                
                audio_content_b64 = response.get("audioContent")
                if not audio_content_b64:
                    raise ValueError("Google no devolvió 'audioContent'.")

                return base64.b64decode(audio_content_b64)

            except Exception as e:
                logger.error(f"GoogleTTS Error: {e}")
                raise e

    async def synthesize_to_file(self, text: str, output_path: str, **kwargs) -> str:
        """Helper para guardar en disco."""
        try:
            audio_bytes = await self.synthesize_speech(text, **kwargs)
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(audio_bytes)
            return output_path
        except Exception as e:
            logger.error(f"GoogleTTS File Error: {e}")
            raise e