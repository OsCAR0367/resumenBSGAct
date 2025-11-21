from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.infrastructure.video.vimeo_downloader import download_video_vimeo
from app.schemas.video_schema import VideoResponse
from app.core.logging_config import logger

load_dotenv()


class VideoService:
    def __init__(self, db: Session):
        self.db = db
        self.access_token = os.getenv("VIMEO_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("VIMEO_ACCESS_TOKEN is missing in environment variables")
    
    async def download_video(self, vimeo_url: str, download_directory: str) -> VideoResponse:
        """
        Descarga un video desde Vimeo
        """
        try:
            logger.info(f"Iniciando descarga de video desde: {vimeo_url}")
            
            # Llamar directamente a la función original
            file_path = download_video_vimeo(vimeo_url, download_directory, self.access_token)
            
            logger.info(f"Video descargado exitosamente en: {file_path}")
            
            return VideoResponse(
                message="Video downloaded successfully",
                file_path=file_path
            )
        
        except Exception as e:
            logger.error(f"Error en VideoService.download_video: {str(e)}")
            raise