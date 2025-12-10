import logging
import os
import aiofiles
from pathlib import Path
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync

# Importamos la infraestructura
from app.infrastructure.llm.openai_summarizer import OpenAISummarizer
# Importamos el repositorio (asumiendo que está en app.infrastructure.repositories)
from app.infrastructure.repositories.procesamiento_repository import ProcesamientoRepository

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        self.summarizer = OpenAISummarizer()
        self.repository = ProcesamientoRepository(db)

    async def generate_and_save_summary(self, session_id: int, transcription_text: str) -> str:
        """
        1. Genera el resumen con OpenAI.
        2. Guarda el archivo .txt en disco (backup).
        3. Actualiza la base de datos con el resumen.
        """
        try:
            logger.info(f"Servicio: Iniciando resumen para sesión {session_id}")
            
            # 1. Llamada a OpenAI
            summary_text = await self.summarizer.generate_summary(transcription_text)

            # 2. Guardar respaldo en disco (Asíncrono)
            output_dir = "data/output/summaries"
            os.makedirs(output_dir, exist_ok=True)
            file_path = Path(output_dir) / f"summary_{session_id}.txt"
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(summary_text)
            
            logger.info(f"Resumen guardado en disco: {file_path}")

            # 3. Actualizar Base de Datos
            # Nota: Las llamadas a BD con SQLAlchemy suelen ser síncronas a menos que uses AsyncSession.
            # Si tu repositorio es síncrono, está bien llamarlo aquí directamente si la operación es rápida,
            # o envolverlo en asyncio.to_thread si la BD es lenta.
            self.repository.update_summarization(
                sesion_id=session_id, 
                success=True, 
                summary_text=summary_text
            )
            
            return summary_text

        except Exception as e:
            logger.error(f"Fallo en SummarizationService: {e}")
            # Registrar error en BD
            try:
                self.repository.update_summarization(session_id, False, "")
            except:
                pass
            raise e