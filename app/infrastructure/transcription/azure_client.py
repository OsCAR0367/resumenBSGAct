import aiohttp
import asyncio
import logging
import json
from app.daemons.config import Config

logger = logging.getLogger(__name__)

class AzureTranscriptionError(Exception):
    pass

class AzureSpeechClient:
    """
    Cliente asíncrono para la API Batch de Azure Speech-to-Text.
    """
    def __init__(self):
        self.api_key = Config.AZURE_SPEECH_KEY
        self.region = Config.AZURE_SPEECH_REGION
        self.api_version = "2024-11-15"
        
        # Limpieza de URL de región por si viene con protocolo
        region_clean = self.region.replace("https://", "").replace("http://", "").split(".")[0]
        self.base_url = f"https://{region_clean}.api.cognitive.microsoft.com/speechtotext/transcriptions:submit"

    async def submit_job(self, sas_url: str, job_name: str) -> str:
        """Envía el trabajo y retorna la URL de polling."""
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "contentUrls": [sas_url],
            "locale": "es-ES",
            "displayName": job_name,
            "properties": {"timeToLiveHours": 48}
        }
        
        url = f"{self.base_url}?api-version={self.api_version}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise AzureTranscriptionError(f"Fallo al enviar trabajo: {resp.status} - {text}")
                
                # Obtener URL de monitoreo del header
                location = resp.headers.get("Location")
                if not location:
                    raise AzureTranscriptionError("Azure no devolvió header Location")
                
                # Ajustar URL para polling (quitar :submit)
                return location.replace(":submit/", "/")

    async def poll_until_complete(self, polling_url: str, interval: int = 5) -> dict:
        """Consulta el estado cada 'interval' segundos sin bloquear."""
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(polling_url, headers=headers) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise AzureTranscriptionError(f"Error en polling: {text}")
                    
                    job_json = await resp.json()
                    status = job_json.get("status")
                    
                    logger.info(f"Estado transcripción: {status}")
                    
                    if status == "Succeeded":
                        return job_json
                    elif status == "Failed":
                        raise AzureTranscriptionError(f"Transcripción falló: {job_json}")
                    
                    # Espera NO bloqueante
                    await asyncio.sleep(interval)

    async def fetch_transcript_text(self, job_json: dict) -> str:
        """Descarga el texto final desde los enlaces del JSON del trabajo."""
        files_url = job_json.get("links", {}).get("files")
        if not files_url:
            raise AzureTranscriptionError("No se encontró link de archivos en la respuesta")
            
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        
        async with aiohttp.ClientSession() as session:
            # 1. Obtener lista de archivos
            async with session.get(files_url, headers=headers) as resp:
                files_data = await resp.json()
            
            # 2. Buscar el archivo de tipo 'transcription'
            for item in files_data.get("values", []):
                if item.get("kind") == "Transcription":
                    content_url = item.get("links", {}).get("contentUrl")
                    
                    # 3. Descargar contenido del JSON de transcripción
                    async with session.get(content_url) as content_resp:
                        result_json = await content_resp.json()
                        
                        # Unir frases
                        phrases = result_json.get("combinedRecognizedPhrases", [])
                        full_text = "\n".join([p.get("display", "") for p in phrases])
                        return full_text
                        
        raise AzureTranscriptionError("No se encontró archivo de transcripción en los resultados")