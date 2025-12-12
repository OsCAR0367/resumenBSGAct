import asyncio
import logging
import subprocess
from pathlib import Path
import re
import os
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

class AudioExtractionError(Exception):
    pass

def _extract_audio_sync(video_path: str, output_path: str, ffmpeg_binary: str):
    """
    Función síncrona interna que ejecuta FFmpeg usando subprocess.run (Más estable en Windows).
    """
    cmd = [
        ffmpeg_binary,
        "-y",               # Sobrescribir
        "-i", video_path,   # Input
        "-vn",              # Sin video
        "-ac", "1",         # Mono
        "-ar", "16000",     # 16kHz
        "-c:a", "libmp3lame",
        "-b:a", "32k",      # Bitrate
        "-f", "mp3",
        output_path
    ]

    logger.info(f"Ejecutando comando FFmpeg: {' '.join(cmd)}")

    # Usamos subprocess.run que es más robusto capturando errores
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_details = result.stderr.strip()
        raise AudioExtractionError(f"FFmpeg falló (Código {result.returncode}): {error_details}")

    return output_path

async def extract_audio_async(video_path: str, output_directory: str = None) -> str:
    """
    Wrapper asíncrono para la extracción de audio.
    """
    video_p = Path(video_path)

    if not video_p.exists():
        raise FileNotFoundError(f"Video no encontrado: {video_path}")

    # 1. Preparar rutas
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)
        safe_stem = re.sub(r"[^\w.-]+", "_", video_p.stem)
        audio_p = Path(output_directory) / f"{safe_stem}.mp3"
    else:
        safe_stem = re.sub(r"[^\w.-]+", "_", video_p.stem)
        audio_p = video_p.parent / f"{safe_stem}.mp3"

    output_path_str = str(audio_p)
    
    # 2. Obtener binario y validar
    ffmpeg_cmd = settings.FFMPEG_BINARY_PATH
    if not os.path.exists(ffmpeg_cmd):
        # Fallback inteligente: si la ruta config no existe, prueba el comando global
        logger.warning(f"No se encontró FFmpeg en {ffmpeg_cmd}, probando comando global 'ffmpeg'")
        ffmpeg_cmd = "ffmpeg"

    logger.info(f"Iniciando extracción: {video_p.name} -> {audio_p.name}")

    try:
        # 3. Ejecutar la función síncrona en un hilo aparte para no bloquear el servidor
        await asyncio.to_thread(_extract_audio_sync, str(video_p), output_path_str, ffmpeg_cmd)

        logger.info(f"Extracción completada: {output_path_str}")
        return output_path_str

    except AudioExtractionError:
        raise
    except Exception as e:
        # Usamos repr(e) para ver el error real si str(e) viene vacío
        logger.error(f"Error inesperado en extracción: {repr(e)}")
        raise AudioExtractionError(f"Fallo sistémico al extraer audio: {repr(e)}")