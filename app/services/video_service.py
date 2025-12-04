import os
import logging
from dotenv import load_dotenv

from app.infrastructure.video.vimeo_downloader import download_video_vimeo_async
from app.schemas.video_schema import VideoResponse

logger = logging.getLogger(__name__)
load_dotenv()

class VideoService:
    def __init__(self):
        self.access_token = os.getenv("VIMEO_ACCESS_TOKEN")
        if not self.access_token:
            logger.warning("VIMEO_ACCESS_TOKEN no configurado en variables de entorno.")
    
    
    async def download_video(self, vimeo_url: str, download_directory: str) -> VideoResponse:
        """
        Orquesta la descarga del video utilizando la implementación nativa asíncrona.
        No bloquea el loop principal.
        """
        try:
            # Validar token
            if not self.access_token:
                raise ValueError("No se puede descargar: falta VIMEO_ACCESS_TOKEN")

            logger.info(f"Servicio: Iniciando descarga para {vimeo_url}")
            
            # Llamada directa con await (Nativo Async)
            file_path = await download_video_vimeo_async(
                vimeo_url=vimeo_url,
                download_directory=download_directory,
                access_token=self.access_token
            )
            
            logger.info(f"Servicio: Video disponible en {file_path}")
            
            return VideoResponse(
                message="Video downloaded successfully",
                file_path=file_path
            )
        
        except Exception as e:
            logger.error(f"Error crítico en VideoService: {str(e)}")
            raise e