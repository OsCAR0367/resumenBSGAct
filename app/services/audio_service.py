from sqlalchemy.orm import Session

from app.infrastructure.video.audio_extractor import extract_audio_from_video, AudioExtractionError
from app.schemas.audio_schema import AudioResponse
from app.core.logging_config import logger


class AudioService:
    def __init__(self, db: Session):
        self.db = db
    
    async def extract_audio(self, video_path: str, output_directory: str) -> AudioResponse:
        """
        Extrae audio de un video
        """
        try:
            logger.info(f"Iniciando extracción de audio desde: {video_path}")
            
            # Llamar a la función de extracción de audio
            audio_path = extract_audio_from_video(video_path)
            
            logger.info(f"Audio extraído exitosamente en: {audio_path}")
            
            return AudioResponse(
                message="Audio extracted successfully",
                audio_path=audio_path
            )
        
        except AudioExtractionError as e:
            logger.error(f"Audio extraction failed: {str(e)}")
            raise Exception(f"Audio extraction failed: {e}")
        except Exception as e:
            logger.error(f"Error en AudioService.extract_audio: {str(e)}")
            raise