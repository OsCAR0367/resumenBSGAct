import logging
import os
import asyncio
import gc
from pathlib import Path
from openai import AsyncOpenAI
from google.cloud import texttospeech
from pydub import AudioSegment
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

# Configurar credenciales de Google si están definidas
if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS

class PodcastGenerator:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # Cliente Google TTS (se usará de forma síncrona dentro de un thread)
        self.voice_name = 'es-US-Polyglot-1'

    async def generate_script(self, summary_text: str) -> str:
        """
        Genera el guion del podcast usando GPT (Etapa 6).
        """
        logger.info("Generando guion con OpenAI...")
        prompt = f"""
        Eres un experto en narraciones educativas.
        Objetivo: Parafrasear el siguiente resumen en un guion de podcast fluido y profesional en Español Latinoamericano.
        Estilo: Tipo audiolibro, informativo, directo. Evita frases como "en este resumen" o "a continuación".
        Formato: Texto plano puro (sin markdown, sin guiones de diálogo, sin asteriscos).
        
        Resumen base:
        {summary_text[:15000]} 
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.5
            )
            script = response.choices[0].message.content.strip()
            return script
        except Exception as e:
            logger.error(f"Error generando guion: {e}")
            raise e

    def _generate_audio_sync(self, script_text: str, output_path: str) -> str:
        """
        Lógica síncrona para Google TTS y PyDub (Etapa 7).
        Se ejecutará en un thread aparte.
        """
        try:
            client = texttospeech.TextToSpeechClient()
            
            # Dividir texto para no exceder límites de API
            parts = self._split_text(script_text, 4000)
            temp_files = []
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="es-US",
                name=self.voice_name
            )

            # Generar audio por partes
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            for i, part in enumerate(parts):
                synthesis_input = texttospeech.SynthesisInput(text=part)
                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config
                )
                
                tmp_path = output_file.parent / f"{output_file.stem}_part_{i}.mp3"
                with open(tmp_path, "wb") as f:
                    f.write(response.audio_content)
                temp_files.append(str(tmp_path))

            # Concatenar partes con PyDub
            if temp_files:
                combined = AudioSegment.empty()
                for tf in temp_files:
                    combined += AudioSegment.from_file(tf)
                
                combined.export(str(output_file), format="mp3")
                
                # Limpiar temporales
                for tf in temp_files:
                    try:
                        os.remove(tf)
                    except: pass
            
            return str(output_file)

        except Exception as e:
            logger.error(f"Error en TTS Google: {e}")
            raise e
        finally:
            gc.collect()

    async def generate_audio_file(self, script_text: str, output_path: str) -> str:
        """Wrapper asíncrono para la generación de audio."""
        return await asyncio.to_thread(self._generate_audio_sync, script_text, output_path)

    def _split_text(self, text, max_chars):
        """Helper simple para dividir texto."""
        words = text.split()
        chunks = []
        current = []
        curr_len = 0
        for w in words:
            if curr_len + len(w) + 1 > max_chars:
                chunks.append(' '.join(current))
                current = [w]
                curr_len = len(w) + 1
            else:
                current.append(w)
                curr_len += len(w) + 1
        if current: chunks.append(' '.join(current))
        return chunks