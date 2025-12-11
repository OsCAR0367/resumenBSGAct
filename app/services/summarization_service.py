import logging
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
# Asegúrate de tener este import
from app.infrastructure.llm.openai_summarizer import OpenAISummarizer 

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db
        # Instanciamos la infraestructura de OpenAI
        self.summarizer = OpenAISummarizer()

    async def generate_summary_only(self, transcription_text: str) -> str:
        """
        Genera el resumen usando OpenAI y lo devuelve como texto.
        NO lo guarda en BD aquí. El orquestador recibe este retorno 
        y lo guarda en el campo 'Resultado' de la tabla Detalle.
        """
        try:
            logger.info("Servicio: Iniciando generación de resumen con IA...")
            
            if not transcription_text:
                raise ValueError("El texto de transcripción está vacío o es nulo.")

            # Llamada a la capa de infraestructura (OpenAI)
            summary_text = await self.summarizer.generate_summary(transcription_text)
            
            if not summary_text:
                raise ValueError("La IA devolvió un resumen vacío.")

            logger.info("Servicio: Resumen generado exitosamente.")
            
            # Retornamos el texto para que BigWorkflowService lo guarde
            return summary_text

        except Exception as e:
            logger.error(f"Error en SummarizationService: {e}")
            raise e