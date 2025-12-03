import logging
from sqlalchemy.orm import Session

# Importamos la nueva función asíncrona de infraestructura
from app.infrastructure.video.audio_extractor import extract_audio_async, AudioExtractionError
from app.schemas.audio_schema import AudioResponse

# Logger para la capa de servicio
logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, db: Session):
        self.db = db
    
    async def extract_audio(self, video_path: str, output_directory: str) -> AudioResponse:
        """
        Orquesta la extracción de audio invocando la infraestructura asíncrona.
        
        Args:
            video_path: Ruta del video fuente.
            output_directory: Directorio destino para el audio.
            
        Returns:
            AudioResponse: Esquema con la ruta del audio resultante.
        """
        try:
            logger.info(f"Servicio: Solicitando extracción para {video_path}")
            
            # Llamada con AWAIT (Crucial para no bloquear)
            audio_path = await extract_audio_async(
                video_path=video_path,
                output_directory=output_directory
            )
            
            # (Opcional) Aquí podrías actualizar el estado en BD usando self.db
            # Ejemplo: self.repository.update_status(...)

            logger.info(f"Servicio: Audio disponible en {audio_path}")
            
            return AudioResponse(
                message="Audio extracted successfully",
                audio_path=audio_path
            )
        
        except AudioExtractionError as e:
            # Los errores de dominio se propagan o manejan aquí
            logger.warning(f"Error de dominio en extracción: {str(e)}")
            raise e  # O lanzar una HTTPException controlada si prefieres
            
        except Exception as e:
            logger.error(f"Error crítico en AudioService: {str(e)}")
            raise Exception(f"Error interno del servicio de audio: {str(e)}")