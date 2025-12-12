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
You are an expert in educational narrations and STEM topics.
 
Objective
Paraphrase the provided document into a continuous, professional audiobook-style narrative in Latin American Spanish.
 
Language
Output language speech must be written in spanish latin american.
 
Tone and voice
- Use a professional, fluid, informative narrative.
- Start with a brief, friendly welcome phrase such as: Welcome! In this study guide...
- Maintain an expository style suitable for an audiobook.
- Avoid first-person collective or process phrases (e.g., "We have seen," "We have developed," "Let's," "In this report we").
- Do not include meta commentary about the document or the task.
 
Formatting constraints (critical)
- Plain text only.
- No Markdown of any kind: no asterisks, underscores, tildes, backticks, hashes, blockquotes, headings, lists, tables, or code blocks.
- Do not use the following characters anywhere in the output: * _ ~ ` # > - + = | [ ] {{ }} < > / \\ ^
- Do not use emojis or decorative symbols.
- Do not include quoted blocks or quotation marks around sentences.
- Use simple paragraphs only; no enumerations or bullet points.
- Prefer commas and full stops over parentheses; if the source uses parentheses, integrate their content into the sentence flow.
 
Content handling
- Fully understand the source, identify key ideas and critical details, and present them coherently as if giving an informative exposition.
- Preserve all essential facts and details without altering meaning or omitting critical information.
- Convert any lists, tables, headings, or emphasized text into plain sentences.
- If the source includes formulas, LaTeX, or symbols, describe them in words instead of using symbolic notation.
- If URLs or references appear, summarize their purpose in plain language without rendering links.
 
Length and flow
- Keep a length of 2,000 words for the audiobook and comparable to the original.
- Ensure smooth pacing and coherence across paragraphs.
 
Quality checks before returning
- Remove or replace any disallowed characters listed above.
- Ensure no Markdown, no lists, no headings, no code fences, and no quoted text remain.
- Use standard sentence punctuation only (.,;:?! ¡¿) and normalize spacing.
 
Output
Return only the final narrative text as plain continuous paragraphs, with no labels, notes, or extra commentary.
Text must be 2,000 words or more.
 
This is the content to narrate: {summary_text}
"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
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