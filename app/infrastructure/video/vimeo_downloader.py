import logging
import os
import re
import aiohttp
import aiofiles
from aiohttp import ClientSession

# Logger específico para este módulo
logger = logging.getLogger(__name__)

async def download_video_vimeo_async(
        
    vimeo_url: str, 
    download_directory: str, 
    access_token: str
) -> str:
    """
    Descarga un video de Vimeo de manera nativa asíncrona usando aiohttp.
    Maneja su propia ClientSession para asegurar limpieza de recursos.
    
    Args:
        vimeo_url: URL completa del video.
        download_directory: Ruta de la carpeta destino.
        access_token: Token de API de Vimeo.
        
    Returns:
        str: Ruta absoluta del archivo descargado.
    """

    # Asegurar directorio (operación rápida, safe síncrono)
    os.makedirs(download_directory, exist_ok=True)

    # Context Manager para la sesión HTTP
    # Esto es crucial: abre y cierra la conexión limpiamente
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Extraer ID del video
            video_id_match = re.search(r"vimeo\.com/(\d+)", vimeo_url)
            if not video_id_match:
                raise ValueError(f"Formato de URL inválido: {vimeo_url}")
            video_id = video_id_match.group(1)

            # 2. Obtener Metadatos (API Call)
            api_url = f"https://api.vimeo.com/videos/{video_id}"
            headers = {"Authorization": f"Bearer {access_token}"}

            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Error API Vimeo ({response.status}): {text}")
                
                video_data = await response.json()
            
            video_name = video_data.get("name", f"video_{video_id}")
            logger.info(f"Metadatos recibidos: '{video_name}'")

            # 3. Buscar enlace de descarga
            files = video_data.get('files', [])
            if not files:
                raise IOError(f"No se encontraron archivos descargables para ID {video_id}. Verifique permisos del Token.")
            
            # Seleccionar resolución (menor altura para rapidez, o ajustar lógica si prefieres HD)
            # Filtramos solo los que tienen 'link' y 'height' válidos
            valid_files = [f for f in files if f.get('link') and f.get('height')]
            if not valid_files:
                raise IOError("Archivos encontrados pero sin enlaces válidos.")
                
            download_info = min(valid_files, key=lambda x: x.get('height', float('inf')))
            download_link = download_info.get('link')
            
            # 4. Preparar nombre de archivo seguro
            safe_title = re.sub(r'[^\w\s-]', '', video_name).strip()
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            file_name = f"{safe_title}.mp4"
            file_path = os.path.join(download_directory, file_name)

            # 5. Descarga Streaming (Chunked)
            logger.info(f"Descargando stream desde: {download_link[:30]}...")
            
            async with session.get(download_link) as stream_response:
                stream_response.raise_for_status()
                
                # Opcional: Log del tamaño
                total_size = int(stream_response.headers.get('content-length', 0))
                
                async with aiofiles.open(file_path, 'wb') as f:
                    # iter_chunked es la clave para no llenar la RAM
                    async for chunk in stream_response.content.iter_chunked(8192):
                        await f.write(chunk)
            
            logger.info(f"Descarga completada: {file_path} ({total_size / (1024*1024):.2f} MB)")
            return file_path

        except aiohttp.ClientError as e:
            logger.error(f"Error de red aiohttp: {e}")
            raise
        except Exception as e:
            logger.error(f"Error general en descarga: {e}")
            # Borrar archivo parcial si falló
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
                logger.warning(f"Archivo parcial eliminado: {file_path}")
            raise