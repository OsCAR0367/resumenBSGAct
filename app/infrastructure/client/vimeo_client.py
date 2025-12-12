import logging
import aiofiles
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.infrastructure.api_client import api_client_async 

logger = logging.getLogger(__name__)

class VimeoClient:
    """
    Cliente estandarizado para interactuar con la API de Vimeo.
    Encapsula autenticación, obtención de metadatos y lógica de descarga.
    """

    def __init__(self, access_token: str, timeout: int = 30):
        """
        Inicializa el cliente de Vimeo con el token de seguridad.
        
        :param access_token: Token Bearer de Vimeo.
        :param timeout: Tiempo máximo de espera para peticiones (default 30s).
        """
        self.base_url = "https://api.vimeo.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.vimeo.*+json;version=3.4",
            "Content-Type": "application/json"
        }
        # Instanciamos el cliente genérico configurado para Vimeo
        self.http_client = api_client_async.ApiClientAsync(
            base_url=self.base_url,
            default_headers=self.headers,
            timeout=timeout
        )

    async def get_video_metadata(self, video_id: str, video_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene la metadata completa de un video (nombre, duración, enlaces de descarga).
        Maneja automáticamente la lógica de videos privados con Hash.
        """
        # Si tiene hash, la ruta es /videos/{id}:{hash}
        if video_hash:
            resource = [f"{video_id}:{video_hash}"]
        else:
            resource = [video_id]

        logger.info(f"VimeoClient: Obteniendo metadata para ID: {video_id}")
        
        # Usamos el cliente genérico con async with para abrir/cerrar conexión
        async with self.http_client as client:
            try:
                response = await client.get_async(endpoint="videos", resource_paths=resource)
                return response
            except Exception as e:
                logger.error(f"VimeoClient Error al obtener metadata: {e}")
                raise e

    def extract_download_link(self, metadata: Dict[str, Any], quality_preference: str = "sd") -> str:
        files = metadata.get('files', [])
        if not files:
            raise ValueError("No se encontraron archivos en la metadata.")

        # FILTRO:
        # 1. Que tenga 'link'
        # 2. Que el tipo sea 'video/mp4' 
        # 3. Que tenga 'height' definido (no sea None)
        valid_files = [
            f for f in files 
            if f.get('link') 
            and f.get('type') == 'video/mp4' 
            and f.get('height') is not None
        ]
        
        if not valid_files:
            raise ValueError("No se encontraron archivos MP4 válidos para descargar.")

        # Ordenar por calidad (height)
        valid_files.sort(key=lambda x: int(x['height']))

        if quality_preference == 'hd':
            selected = valid_files[-1] # El más grande
        else:
            selected = valid_files[0]  # El más pequeño (SD)

        logger.info(f"VimeoClient: Calidad seleccionada: {selected.get('height')}p (MP4)")
        return selected.get('link')

    async def download_video_file(self, download_url: str, save_path: str) -> str:
        """
        Descarga el archivo binario desde la CDN de Vimeo.
        NOTA: Vimeo CDN requiere User-Agent de navegador para no dar 403.
        """
        # Headers específicos para el CDN de Vimeo
        cdn_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://vimeo.com/"
        }

        # Usamos una instancia nueva del cliente genérico porque la URL base es distinta (CDN)
        # y necesitamos headers diferentes a los de la API.
        downloader = api_client_async.ApiClientAsync(base_url="", default_headers=cdn_headers, timeout=300) # Timeout largo para descargas

        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"VimeoClient: Iniciando descarga en {save_path}...")

        async with downloader as client:
            # Usamos el modo stream del cliente genérico
            # endpoint=download_url (URL completa)
            try:
                stream_context = await client.request_async(
                    endpoint=download_url, 
                    stream=True, 
                    method="GET"
                )
                
                async with stream_context as response:
                    response.raise_for_status()
                    async with aiofiles.open(save_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            await f.write(chunk)
                
                logger.info("VimeoClient: Descarga completada.")
                return str(path)
            
            except Exception as e:
                logger.error(f"VimeoClient Error en descarga: {e}")
                # Limpieza si falla
                if path.exists():
                    path.unlink()
                raise e

    # Método Helper para Facilidad de Uso
    async def process_video_url(self, vimeo_full_url: str, output_dir: str, file_prefix: str = "") -> str:
        """
        Método 'All-in-One': Recibe URL web -> Descarga Video.
        """
        # 1. Parsear URL
        match = re.search(r"vimeo\.com/(\d+)(?:/([a-zA-Z0-9]+))?", vimeo_full_url)
        if not match:
            raise ValueError(f"URL Vimeo inválida: {vimeo_full_url}")
        
        video_id = match.group(1)
        video_hash = match.group(2)

        # 2. Obtener Metadata
        meta = await self.get_video_metadata(video_id, video_hash)
        
        # 3. Obtener Link
        link = self.extract_download_link(meta, quality_preference="sd")
        
        # 4. Definir Nombre
        clean_name = re.sub(r'[^\w\s-]', '', meta.get('name', 'video')).strip().replace(' ', '_')
        filename = f"{file_prefix}_{clean_name}.mp4" if file_prefix else f"{clean_name}.mp4"
        full_path = str(Path(output_dir) / filename)

        # 5. Descargar
        return await self.download_video_file(link, full_path)