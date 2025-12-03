import os
import logging
from openai import AsyncOpenAI
from app.daemons.config import Config

logger = logging.getLogger(__name__)

class OpenAISummarizer:
    """
    Cliente asíncrono para generar resúmenes con OpenAI.
    """
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no configurada.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)

    def _get_analysis_prompt(self, transcription: str) -> str:
        """
        Genera el prompt con la estructura educativa original y completa.
        (Copiado textualmente de la versión anterior para mantener la lógica).
        """
        return f"""
Objective
 
Condense the provided transcription to approximately 4,000 words, focusing strictly on the main educational concepts, central topics, and significant subtopics discussed during the session. The summary must maintain a formal, clear, and professional tone and should closely follow the original order of topics and subtopics, without omitting any key sections. Non-essential information, including pending class arrangements or agreements, should be treated only as secondary content and summarized exclusively at the end. The entire output must be written in Spanish.
 
Specific Instructions:
General Summary of the Session:
 
Provide a clear and coherent overview of the educational topics addressed during the session, correcting any grammatical or stylistic errors if necessary.
 
Include only educationally relevant information from the transcript in this section.
 
Detailed Development of Topics:
 
For each 2.x topic [Topic Name], follow this structure:
 
Conceptual Development: Clearly explain the main educational concepts, ensuring precision and clarity.
 
Practical or Illustrative Examples: Summarize the most important examples or case studies included in the transcript, improving clarity while remaining faithful to the original content.
 
Relevance and Application: Describe the importance and real-world application of the topics discussed, using only information directly relevant from the transcript.
 
Continue with subsequent topics using the same structured format.
 
Activities or Assigned Tasks:
 
At the end of the summary, list only the activities, tasks, or projects explicitly mentioned during the session, improving their clarity but without including unrelated content. Summarize class rescheduling agreements or pending activities here only, as a secondary aspect.
 
Style and Formatting:
 
Maintain a formal, professional, and polished tone throughout, avoiding redundancy, informal language, or irrelevant details.
 
Organize content using clear hierarchical headings and subheadings to ensure readability and logical flow.
 
Limit the summary to approximately 4,000 words, providing sufficient detail on key educational matters while excluding extraneous information.
 
The output must be written in Spanish.
 
Output Format:
 
Begin with an introductory paragraph for the General Summary of the Session.
 
Use a clear hierarchical structure with numbered subheadings (2.x) for the Detailed Development of Topics.
 
For each topic, use delineated subheadings for Conceptual Development, Practical Examples, and Relevance and Application.
 
Conclude with a final section, Activities or Assigned Tasks, presented as a concise, clear list.
 
Notes:
 
Ensure logical coherence and fluency throughout the summary.
 
Make sure all essential educational concepts and relevant examples are included and clarified where possible.
 
Correct any grammatical or stylistic errors to ensure a highly professional text.
 
The output must consist only of the summary according to these instructions; do not add anything else such as introductory statements or meta-comments.
 
{transcription}
"""

    async def generate_summary(self, transcription_text: str, model: str = "gpt-4o") -> str:
        """
        Envía el texto a OpenAI y retorna el resumen de forma asíncrona.
        """
        try:
            if not transcription_text:
                raise ValueError("El texto de transcripción está vacío.")

            prompt = self._get_analysis_prompt(transcription_text)
            
            logger.info(f"Enviando solicitud de resumen a OpenAI (Modelo: {model})...")
            
            # Llamada asíncrona a la API
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=16384,
                temperature=0.0
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info("Resumen generado exitosamente.")
            return summary

        except Exception as e:
            logger.error(f"Error generando resumen con OpenAI: {e}")
            raise e